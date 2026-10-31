"""
Walmart sales dashboard built from the dbt marts tables in Snowflake.

Setup (once):
    conda create -n walmart python=3.11 -y
    conda activate walmart
    pip install "snowflake-connector-python[pandas]" matplotlib streamlit python-dotenv

Connection settings come from environment variables, or from a .env file
next to this script:
    SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_WAREHOUSE,
    SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA   (the schema dbt built the marts into)
    SNOWFLAKE_PASSWORD                     (omit when using browser login)
    SNOWFLAKE_AUTHENTICATOR                optional, e.g. "externalbrowser" for SSO/MFA
    SNOWFLAKE_ROLE                         optional

Run:
    streamlit run walmart_charts.py

Every chart is shown in the browser and also saved as a PNG in ./charts.
"""

import calendar
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no GUI windows; Streamlit renders the figures

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import snowflake.connector
import streamlit as st
from matplotlib.patches import Patch

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).with_name(".env"))
except ImportError:
    pass

st.set_page_config(page_title="Walmart Sales", layout="wide")

OUT_DIR = Path(__file__).resolve().parent / "charts"
OUT_DIR.mkdir(exist_ok=True)

MONTH_NAMES = [calendar.month_name[m] for m in range(1, 13)]
MARKDOWN_COLS = [f"MARKDOWN{i}" for i in range(1, 6)]
NUMERIC_COLS = [
    "STORE_SIZE", "WEEKLY_SALES", "TEMPERATURE", "FUEL_PRICE",
    "CPI", "UNEMPLOYMENT", *MARKDOWN_COLS,
]
TYPE_COLORS = {"A": "cornflowerblue", "B": "darkslategray", "C": "salmon"}
BAR_COLOR = "deepskyblue"


# ---------------------------------------------------------------------------
# Queries
# Only current versions (VRSN_END_DATE IS NULL) so SCD2 history isn't
# double counted. Store-level features (fuel, CPI, markdowns, size) repeat on
# every department row, so they're collapsed with MAX at store-week grain
# while sales are summed across departments.
# ---------------------------------------------------------------------------
STORE_WEEK_SQL = """
SELECT
    d.STORE_DATE,
    d.ISHOLIDAY,
    f.STORE_ID,
    s.STORE_TYPE,
    MAX(f.STORE_SIZE)          AS STORE_SIZE,
    SUM(f.STORE_WEEKLY_SALES)  AS WEEKLY_SALES,
    MAX(f.TEMPERATURE)         AS TEMPERATURE,
    MAX(f.FUEL_PRICE)          AS FUEL_PRICE,
    MAX(f.CPI)                 AS CPI,
    MAX(f.UNEMPLOYMENT)        AS UNEMPLOYMENT,
    MAX(f.MARKDOWN1)           AS MARKDOWN1,
    MAX(f.MARKDOWN2)           AS MARKDOWN2,
    MAX(f.MARKDOWN3)           AS MARKDOWN3,
    MAX(f.MARKDOWN4)           AS MARKDOWN4,
    MAX(f.MARKDOWN5)           AS MARKDOWN5
FROM WALMART_FACT_TABLE AS f
JOIN WALMART_DATE_DIM   AS d ON f.DATE_ID = d.DATE_ID
JOIN WALMART_STORE_DIM  AS s ON f.STORE_ID = s.STORE_ID AND f.DEPT_ID = s.DEPT_ID
WHERE f.VRSN_END_DATE IS NULL
GROUP BY d.STORE_DATE, d.ISHOLIDAY, f.STORE_ID, s.STORE_TYPE
"""

# Total sales per department across all stores and weeks.
DEPT_SQL = """
SELECT
    f.DEPT_ID,
    SUM(f.STORE_WEEKLY_SALES) AS WEEKLY_SALES
FROM WALMART_ANALYTICS.MARTS.WALMART_FACT_TABLE AS f
WHERE f.VRSN_END_DATE IS NULL
GROUP BY f.DEPT_ID
ORDER BY f.DEPT_ID
"""


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def connect():
    params = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
        "database": os.environ["SNOWFLAKE_DATABASE"],
        "schema": os.environ["SNOWFLAKE_SCHEMA"],
        "enable_server_session_keep_alive_auto_detection": True,
    }
    if os.environ.get("SNOWFLAKE_AUTHENTICATOR"):
        params["authenticator"] = os.environ["SNOWFLAKE_AUTHENTICATOR"]
    else:
        params["password"] = os.environ["SNOWFLAKE_PASSWORD"]
    if os.environ.get("SNOWFLAKE_ROLE"):
        params["role"] = os.environ["SNOWFLAKE_ROLE"]
    return snowflake.connector.connect(**params)


def query(conn, sql):
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetch_pandas_all()


def prepare_store_week(sw):
    """Fix types once and add the date parts the charts group by."""
    sw["STORE_DATE"] = pd.to_datetime(sw["STORE_DATE"])
    sw["ISHOLIDAY"] = sw["ISHOLIDAY"].astype(str).str.upper().isin(["TRUE", "1"])
    sw["STORE_TYPE"] = sw["STORE_TYPE"].astype(str)
    sw[NUMERIC_COLS] = sw[NUMERIC_COLS].apply(pd.to_numeric, errors="coerce")
    sw[MARKDOWN_COLS] = sw[MARKDOWN_COLS].fillna(0)
    sw["YEAR"] = sw["STORE_DATE"].dt.year
    sw["MONTH"] = sw["STORE_DATE"].dt.month
    sw["DAY"] = sw["STORE_DATE"].dt.day
    return sw


def prepare_dept(dept):
    dept["WEEKLY_SALES"] = pd.to_numeric(dept["WEEKLY_SALES"], errors="coerce")
    return dept.dropna(subset=["DEPT_ID", "WEEKLY_SALES"])


# Streamlit reruns the whole script on every widget change; caching keeps it
# from re-querying Snowflake each time.
@st.cache_data(ttl=3600, show_spinner="Loading data from Snowflake...")
def load_data():
    conn = connect()
    try:
        sw = query(conn, STORE_WEEK_SQL)
        dept = query(conn, DEPT_SQL)
    finally:
        conn.close()
    return prepare_store_week(sw), prepare_dept(dept)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def short_money(value, unit="M", decimals=0):
    scale = {"M": 1e6, "bn": 1e9}[unit]
    return f"{value / scale:,.{decimals}f}{unit}"


def axis_formatter(unit="M", decimals=0):
    return lambda value, _pos: short_money(value, unit, decimals)


def show(fig):
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)


def save(fig, filename):
    fig.tight_layout()
    fig.savefig(OUT_DIR / filename, dpi=150)
    plt.close(fig)


def show_and_save(fig, filename):
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    fig.savefig(OUT_DIR / filename, dpi=150)
    plt.close(fig)


def with_total_row(df, label="Total"):
    """Append a summed Total row. The index becomes text so the
    mix of IDs and "Total" displays cleanly in st.dataframe."""
    out = df.copy()
    out.index = out.index.astype(str)
    out.loc[label] = df.sum(numeric_only=True)
    return out


def draw_table(ax, rows, col_labels, title, fontsize=8):
    """Static table that stays inside its axes, however many rows it has."""
    ax.axis("off")
    ax.set_title(title)
    table = ax.table(
        cellText=rows,
        colLabels=col_labels,
        cellLoc="right",
        bbox=[0, 0, 1, 0.97],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(fontsize)


def draw_card(ax, value, label):
    ax.text(0.5, 0.58, value, ha="center", va="center", fontsize=22, fontweight="bold")
    ax.text(0.5, 0.38, label, ha="center", va="center", fontsize=13)


def boxed(ax, aspect=1.1):
    ax.set_box_aspect(aspect)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set(visible=True, color="black", linewidth=1)


def label_bars(ax, bars, unit="M", decimals=0, fontsize=8):
    ax.bar_label(
        bars,
        labels=[short_money(v, unit, decimals) for v in bars.datavalues],
        padding=3,
        fontsize=fontsize,
    )
    ax.margins(y=0.15)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def sales_by_store(sw):
    by_store = sw.pivot_table(
        index="STORE_ID", columns="ISHOLIDAY", values="WEEKLY_SALES",
        aggfunc="sum", fill_value=0,
    ).reindex(columns=[False, True], fill_value=0)
    by_holiday = by_store.sum()
    start, end = sw["STORE_DATE"].min(), sw["STORE_DATE"].max()

    fig = plt.figure(figsize=(20, 8))
    grid = fig.add_gridspec(2, 2, width_ratios=[1, 4])
    ax_pie = fig.add_subplot(grid[0, 0])
    ax_card = fig.add_subplot(grid[1, 0])
    ax_bar = fig.add_subplot(grid[:, 1])

    ax_pie.pie(
        by_holiday.values, labels=["False", "True"],
        autopct="%1.1f%%", startangle=90, frame=True,
    )
    ax_pie.set_title("Weekly Sales by IsHoliday")
    boxed(ax_pie)

    draw_card(ax_card, f"${by_holiday.sum() / 1e9:.2f}B", "Total Sales")
    boxed(ax_card)

    by_store.plot(kind="bar", ax=ax_bar, width=0.95)
    ax_bar.set(
        title=f"Total weekly sales by store: {start:%Y-%m-%d} to {end:%Y-%m-%d}",
        xlabel="Store ID", ylabel="Weekly Sales",
    )
    ax_bar.yaxis.set_major_formatter(axis_formatter("M"))
    ax_bar.legend(title="Is Holiday:")
    ax_bar.grid(alpha=0.3)
    for container in ax_bar.containers:
        label_bars(ax_bar, container)

    show_and_save(fig, "01_weekly_sales_by_store.png")


def weekly_sales_waterfall(sw):
    store_id = st.selectbox("Select store", sorted(sw["STORE_ID"].unique()))
    weekly = (
        sw.loc[sw["STORE_ID"] == store_id]
        .groupby("STORE_DATE")["WEEKLY_SALES"]
        .sum()
        .sort_index()
    )
    if weekly.empty:
        st.warning("No weekly sales data for this store.")
        return

    up, down, start, end = "deepskyblue", "dimgray", "gold", "darkslategray"
    sales = weekly.to_numpy()
    change = np.diff(sales)

    # Starting bar, one floating bar per week-to-week change, ending bar.
    bottoms = np.concatenate([[0], np.minimum(sales[:-1], sales[1:]), [0]])
    heights = np.concatenate([[sales[0]], np.abs(change), [sales[-1]]])
    colors = [start, *[up if c >= 0 else down for c in change], end]
    labels = [
        short_money(sales[0], "M", 2),
        *[f"{c / 1e6:+.2f}M" for c in change],
        short_money(sales[-1], "M", 2),
    ]
    ticks = [f"{d:%m/%d/%y}" for d in weekly.index] + ["Ending Sales"]
    x = np.arange(len(ticks))

    fig, ax = plt.subplots(figsize=(max(14, len(ticks) * 0.3), 7))
    bars = ax.bar(x, heights, bottom=bottoms, color=colors, width=0.7)
    ax.bar_label(bars, labels=labels, padding=4, fontsize=8)

    ax.set(title=f"Weekly Sales Waterfall — Store {store_id}", xlabel="Week", ylabel="Weekly Sales")
    ax.set_xticks(x, ticks, rotation=90)
    ax.yaxis.set_major_formatter(axis_formatter("M", 1))
    ax.grid(axis="y", alpha=0.3)
    ax.legend(
        handles=[
            Patch(color=up, label="Increase"),
            Patch(color=down, label="Decrease"),
            Patch(color=start, label="Starting Sales"),
            Patch(color=end, label="Ending Sales"),
        ],
        loc="upper left",
        ncol=4,
    )

    show_and_save(fig, f"02_weekly_sales_waterfall_store_{store_id}.png")


def sales_by_store_size(sw):
    stores = sw.groupby(["STORE_ID", "STORE_SIZE"], as_index=False)["WEEKLY_SALES"].sum()
    by_size = stores.sort_values("STORE_SIZE")
    by_sales = stores.sort_values("WEEKLY_SALES", ascending=False)

    def draw(ax):
        ax.fill_between(by_size["STORE_SIZE"], by_size["WEEKLY_SALES"], color="cornflowerblue", alpha=0.4)
        ax.plot(by_size["STORE_SIZE"], by_size["WEEKLY_SALES"], color="dodgerblue", linewidth=1.5)
        ax.set(title="Sales by Store Size", xlabel="Store Size", ylabel="Weekly Sales")
        ax.yaxis.set_major_formatter(axis_formatter("M"))
        ax.grid(alpha=0.3)

    chart_col, table_col = st.columns([3, 2], gap="medium")
    with chart_col:
        fig, ax = plt.subplots(figsize=(12, 6))
        draw(ax)
        show(fig)
    with table_col:
        st.subheader("Store Sales")
        st.dataframe(by_sales, width="stretch", height=560, hide_index=True)

    # PNG: chart beside a table of every store
    png, (ax_chart, ax_table) = plt.subplots(
        1, 2,
        figsize=(20, max(12, 0.34 * (len(stores) + 1))),
        gridspec_kw={"width_ratios": [2.2, 1]},
    )
    draw(ax_chart)
    rows = [
        [str(r.STORE_ID), f"{r.STORE_SIZE:,.0f}", f"${r.WEEKLY_SALES:,.2f}"]
        for r in by_sales.itertuples(index=False)
    ]
    draw_table(ax_table, rows, ["Store ID", "Size", "Weekly Sales"], "Store Sales")
    save(png, "03_sales_by_store_size.png")


def sales_by_store_type_and_month(sw):
    monthly = sw.pivot_table(
        index="MONTH", columns="STORE_TYPE", values="WEEKLY_SALES",
        aggfunc="sum", fill_value=0,
    ).reindex(range(1, 13), fill_value=0)
    store_types = list(monthly.columns)

    table = monthly.set_axis(MONTH_NAMES)
    table.index.name = "Month"
    table = with_total_row(table)

    def draw(ax):
        x = np.arange(12)
        for store_type in store_types:
            y = monthly[store_type].to_numpy()
            ax.plot(x, y, linewidth=1.5, label=store_type)
            for xi, yi in zip(x, y):
                ax.annotate(
                    short_money(yi), (xi, yi), textcoords="offset points",
                    xytext=(0, 7), ha="center", fontsize=8,
                )
        ax.set(title="Weekly Sales by Store Type and Month", xlabel="Month", ylabel="Weekly Sales")
        ax.set_xticks(x, MONTH_NAMES)
        ax.yaxis.set_major_formatter(axis_formatter("M"))
        ax.legend(title="Store Type")
        ax.grid(alpha=0.3)

    chart_col, table_col = st.columns([3, 2], gap="medium")
    with chart_col:
        fig, ax = plt.subplots(figsize=(12, 6))
        draw(ax)
        show(fig)
    with table_col:
        st.subheader("Monthly Sales by Store Type")
        st.dataframe(table.reset_index(), width="stretch", height=560, hide_index=True)

    png, (ax_chart, ax_table) = plt.subplots(
        1, 2, figsize=(20, 9), gridspec_kw={"width_ratios": [2.2, 1]},
    )
    draw(ax_chart)
    rows = [[month, *[f"${v:,.2f}" for v in row]] for month, row in table.iterrows()]
    draw_table(ax_table, rows, ["Month", *store_types], "Monthly Sales by Store Type")
    save(png, "04_weekly_sales_by_store_type_and_month.png")


def markdown_sales_by_year(sw):
    yearly = sw.groupby("YEAR")[MARKDOWN_COLS].sum().sort_index()
    years = yearly.index.tolist()

    table_col, chart_col = st.columns([1.2, 1.8], gap="medium")

    with table_col:
        year = st.selectbox("Select year for markdown sales", years, index=len(years) - 1)
        by_store = sw.loc[sw["YEAR"] == year].groupby("STORE_ID")[MARKDOWN_COLS].sum()
        st.dataframe(
            with_total_row(by_store).reset_index(),
            width="stretch", height=460, hide_index=True,
        )

    with chart_col:
        fig, ax = plt.subplots(figsize=(12, 7))
        x = np.arange(len(years))
        width = 0.15
        for i, col in enumerate(MARKDOWN_COLS):
            offset = (i - (len(MARKDOWN_COLS) - 1) / 2) * width
            bars = ax.bar(x + offset, yearly[col], width=width, label=col)
            label_bars(ax, bars, "bn", 3, fontsize=7)
        ax.set(title="Markdown Sales by Year", xlabel="Year", ylabel="Markdown Sales")
        ax.set_xticks(x, years)
        ax.yaxis.set_major_formatter(axis_formatter("bn", 1))
        ax.legend(title="Markdown")
        ax.grid(axis="y", alpha=0.3)
        show_and_save(fig, "05_markdown_sales_by_year.png")


def sales_by_store_type(sw):
    store_sales = sw.groupby(["STORE_TYPE", "STORE_ID"], as_index=False)["WEEKLY_SALES"].sum()
    types = sorted(store_sales["STORE_TYPE"].unique())

    selected = st.multiselect("Select store type", options=types, default=types)
    if not selected:
        st.info("Select at least one store type.")
        return
    order = sorted(selected)

    bars = (
        store_sales[store_sales["STORE_TYPE"].isin(order)]
        .sort_values(["STORE_TYPE", "STORE_ID"])
        .reset_index(drop=True)
    )
    # One row per store, with a blank row between store types
    bars["Y"] = bars.index + bars["STORE_TYPE"].map({t: i for i, t in enumerate(order)})
    type_totals = bars.groupby("STORE_TYPE")["WEEKLY_SALES"].sum()
    type_centers = bars.groupby("STORE_TYPE")["Y"].mean()

    store_ids = sorted(bars["STORE_ID"].unique())
    store_colors = dict(zip(store_ids, plt.cm.turbo(np.linspace(0, 1, len(store_ids)))))

    fig, (ax_pie, ax_bar) = plt.subplots(
        1, 2,
        figsize=(18, max(8, 0.22 * len(bars))),
        gridspec_kw={"width_ratios": [1, 2.3]},
    )

    ax_pie.pie(
        type_totals.values,
        labels=type_totals.index,
        colors=[TYPE_COLORS.get(t, "gray") for t in type_totals.index],
        startangle=90,
    )
    ax_pie.set_title("Weekly Sales by Store Type")
    ax_pie.axis("equal")

    ax_bar.barh(
        bars["Y"], bars["WEEKLY_SALES"],
        color=[store_colors[s] for s in bars["STORE_ID"]],
        height=0.75,
    )
    for y, sales in zip(bars["Y"], bars["WEEKLY_SALES"]):
        ax_bar.text(sales, y, f"  {short_money(sales)}", va="center", fontsize=7)

    ax_bar.set_yticks(type_centers.values, type_centers.index)
    ax_bar.invert_yaxis()
    ax_bar.set(title="Weekly Sales by Store and Type", xlabel="Weekly Sales")
    ax_bar.xaxis.set_major_formatter(axis_formatter("M"))
    ax_bar.grid(axis="x", alpha=0.3)
    ax_bar.legend(
        handles=[Patch(color=store_colors[s], label=str(s)) for s in store_ids],
        title="Store ID",
        loc="lower left",
        bbox_to_anchor=(0, 1.01),
        ncol=min(8, len(store_ids)),
        fontsize=7,
    )

    show_and_save(fig, "06_weekly_sales_by_store_type.png")


def fuel_price_by_year(sw):
    fuel = sw.dropna(subset=["FUEL_PRICE"])

    by_store_year = fuel.pivot_table(
        index="STORE_ID", columns="YEAR", values="FUEL_PRICE",
        aggfunc="sum", fill_value=0,
    )
    # Text column names: mixing int years with "Total" caused the Arrow warning
    by_store_year.columns = by_store_year.columns.astype(str)
    by_store_year["Total"] = by_store_year.sum(axis=1)
    table = with_total_row(by_store_year)

    by_year = fuel.groupby("YEAR")["FUEL_PRICE"].sum()
    total = by_year.sum()

    def draw_donut(ax):
        ax.pie(by_year.values, labels=by_year.index.astype(str), startangle=90, wedgeprops={"width": 0.45})
        ax.set_title("Fuel Price by Year")
        ax.axis("equal")

    def draw_total(ax):
        ax.axis("off")
        draw_card(ax, f"{total:,.0f}", "Fuel_Price")

    table_col, chart_col = st.columns([1.5, 1])
    with table_col:
        st.dataframe(table.reset_index(), width="stretch", height=560, hide_index=True)
    with chart_col:
        fig = plt.figure(figsize=(6, 7))
        grid = fig.add_gridspec(2, 1, height_ratios=[1.2, 0.8])
        draw_donut(fig.add_subplot(grid[0]))
        draw_total(fig.add_subplot(grid[1]))
        show(fig)

    # PNG: table, donut, and total card together
    png = plt.figure(figsize=(16, 9))
    grid = png.add_gridspec(2, 2, width_ratios=[1.5, 1], height_ratios=[1.2, 0.8])
    rows = [[store, *[f"{v:,.2f}" for v in row]] for store, row in table.iterrows()]
    draw_table(
        png.add_subplot(grid[:, 0]), rows,
        ["Store", *by_store_year.columns], "Fuel Price by Store and Year", fontsize=7,
    )
    draw_donut(png.add_subplot(grid[0, 1]))
    draw_total(png.add_subplot(grid[1, 1]))
    save(png, "07_fuel_price_by_year.png")


def sales_by_year_month_day(sw):
    by_year = sw.groupby("YEAR")["WEEKLY_SALES"].sum()
    by_month = sw.groupby("MONTH")["WEEKLY_SALES"].sum().reindex(range(1, 13), fill_value=0)
    by_day = sw.groupby("DAY")["WEEKLY_SALES"].sum().reindex(range(1, 32), fill_value=0)

    fig = plt.figure(figsize=(16, 10))
    grid = fig.add_gridspec(2, 2, height_ratios=[1, 1.1], width_ratios=[1, 1.6])
    ax_year = fig.add_subplot(grid[0, 0])
    ax_month = fig.add_subplot(grid[0, 1])
    ax_day = fig.add_subplot(grid[1, :])

    panels = [
        (ax_year, by_year.index.astype(str), by_year, "Weekly Sales by Year", "bn", 2),
        (ax_month, MONTH_NAMES, by_month, "Weekly Sales by Month", "bn", 2),
        (ax_day, by_day.index, by_day, "Weekly Sales by Day of Month", "M", 0),
    ]
    for ax, x, values, title, unit, decimals in panels:
        bars = ax.bar(x, values.values, color=BAR_COLOR)
        label_bars(ax, bars, unit, decimals)
        ax.set(title=title, ylabel="Weekly Sales")
        ax.yaxis.set_major_formatter(axis_formatter(unit, 1 if unit == "bn" else 0))
        ax.grid(axis="y", alpha=0.3)

    ax_month.tick_params(axis="x", rotation=35)
    ax_day.set_xlabel("Day of Month")
    ax_day.set_xticks(range(1, 32))

    show_and_save(fig, "08_weekly_sales_by_year_month_day.png")


def sales_by_cpi(sw):
    data = sw.dropna(subset=["CPI", "WEEKLY_SALES"])

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.scatter(data["CPI"], data["WEEKLY_SALES"], color="dodgerblue", s=12, alpha=0.45)
    ax.set(title="Weekly Sales by CPI", xlabel="CPI", ylabel="Weekly Sales")
    ax.yaxis.set_major_formatter(axis_formatter("M"))
    ax.grid(alpha=0.3)

    show_and_save(fig, "09_weekly_sales_by_cpi.png")


def department_weekly_sales(dept):
    totals = dept.sort_values("DEPT_ID")
    top_five = totals.nlargest(5, "WEEKLY_SALES")
    columns = {
        "DEPT_ID": st.column_config.NumberColumn("Department"),
        "WEEKLY_SALES": st.column_config.NumberColumn("Weekly Sales", format="$%,.2f"),
    }

    st.title("Department-Wise Weekly Sales")

    table_col, total_col, top_col = st.columns([1.2, 1, 1.2])
    with table_col:
        st.subheader("Sales by Department")  # click a column heading to sort
        st.dataframe(totals, width="stretch", height=230, hide_index=True, column_config=columns)
    with total_col:
        st.subheader("Total Sales")
        st.metric("Weekly Sales", f"${totals['WEEKLY_SALES'].sum() / 1e9:.3f}bn")
    with top_col:
        st.subheader("Top 5 Departments by Sales")
        st.dataframe(top_five, width="stretch", height=230, hide_index=True, column_config=columns)

    fig, ax = plt.subplots(figsize=(16, 6))
    x = np.arange(len(totals))
    ax.bar(x, totals["WEEKLY_SALES"], color="cornflowerblue", width=0.8)
    ax.set_xticks(x, totals["DEPT_ID"].astype(str))
    ax.set(title="Total Weekly Sales by Department", xlabel="Department", ylabel="Weekly Sales")
    ax.yaxis.set_major_formatter(lambda value, _pos: f"${value / 1e9:.1f}bn")
    ax.grid(axis="y", alpha=0.3)

    show_and_save(fig, "10_department_wise_weekly_sales.png")


# ---------------------------------------------------------------------------
def main():
    st.title("Walmart Sales")
    sw, dept = load_data()

    sales_by_store(sw)
    weekly_sales_waterfall(sw)
    sales_by_store_size(sw)
    sales_by_store_type_and_month(sw)
    markdown_sales_by_year(sw)
    sales_by_store_type(sw)
    fuel_price_by_year(sw)
    sales_by_year_month_day(sw)
    sales_by_cpi(sw)
    department_weekly_sales(dept)


if __name__ == "__main__":
    main()