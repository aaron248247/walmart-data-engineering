
"""
Walmart sales charts from the dbt marts tables in Snowflake.

Setup (once, in its own environment):
    conda create -n walmart python=3.11 -y
    conda activate walmart
    pip install "snowflake-connector-python[pandas]" matplotlib

Connection details are read from environment variables so no password
lives in the code. In PowerShell, before running:
    $env:SNOWFLAKE_ACCOUNT   = "xy12345.us-east-1"
    $env:SNOWFLAKE_USER      = "AARON"
    $env:SNOWFLAKE_PASSWORD  = "..."          # omit if using browser login
    $env:SNOWFLAKE_AUTHENTICATOR = "externalbrowser"   # optional, for SSO/MFA
    $env:SNOWFLAKE_WAREHOUSE = "COMPUTE_WH"
    $env:SNOWFLAKE_DATABASE  = "WALMART_DB"
    $env:SNOWFLAKE_SCHEMA    = "DEV_MARTS"    # the schema dbt built the marts into
    $env:SNOWFLAKE_ROLE      = "..."          # optional

Run:
    python walmart_charts.py
Charts are saved as PNGs in ./charts
"""

import os
from pathlib import Path
import calendar
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import snowflake.connector
from plotly.subplots import make_subplots
from matplotlib.ticker import FuncFormatter

# Load connection settings from a .env file next to this script, if present.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).with_name(".env"))
except ImportError:
    pass

# Save next to this script (python/charts), wherever it's run from.
OUT_DIR = Path(__file__).resolve().parent / "charts"
OUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Connection
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

DEPT_SQL = """
SELECT
    d.STORE_DATE,
    f.DEPT_ID,
    SUM(f.STORE_WEEKLY_SALES) AS WEEKLY_SALES
FROM WALMART_ANALYTICS.MARTS.WALMART_FACT_TABLE AS f
JOIN WALMART_ANALYTICS.MARTS.WALMART_DATE_DIM AS d
    ON f.DATE_ID = d.DATE_ID
WHERE f.VRSN_END_DATE IS NULL
GROUP BY d.STORE_DATE, f.DEPT_ID
"""


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def save(fig, name):
    path = OUT_DIR / name
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"saved {path}")


def millions(x, _pos=None):
    return f"${x / 1e6:,.0f}M"

def add_black_square(ax, aspect=1):
    ax.set_box_aspect(aspect)  
    ax.set_xticks([])
    ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("black")
        spine.set_linewidth(1)

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def chart_sales_by_store(sw):
    chart_data = (
        sw.groupby(["STORE_ID", "ISHOLIDAY"])["WEEKLY_SALES"]
    .sum()
    .unstack(fill_value=0)
    .reindex(columns=[False,True], fill_value=0)
    .sort_index()
    )


    holiday_sales = (
    sw.groupby("ISHOLIDAY")["WEEKLY_SALES"]
        .sum()
        .reindex([False, True], fill_value=0)
    )

    total_sales = sw["WEEKLY_SALES"].sum()

    min_date = sw["STORE_DATE"].min().strftime("%Y-%m-%d")
    max_date = sw["STORE_DATE"].max().strftime("%Y-%m-%d")

    # Left column: pie and total-sales card. Right: bar chart.
    fig = plt.figure(figsize=(20, 8))
    layout = fig.add_gridspec(
        2, 2,
        width_ratios=[1, 4],
        height_ratios=[1, 1]
    )

    ax_pie = fig.add_subplot(layout[0, 0])
    ax_total = fig.add_subplot(layout[1, 0])
    ax_bar = fig.add_subplot(layout[:, 1])

    # Pie chart
    ax_pie.pie(
        holiday_sales.values,
        labels=["False", "True"],
        autopct="%1.1f%%",
        startangle=90,
        frame=True
    )
    ax_pie.set_title("Weekly Sales by IsHoliday")
    add_black_square(ax_pie, aspect=1.10)

    # Total-sales figure
    
    ax_total.text(0.5, 0.60, "Total Sales:", ha="center", fontsize=16)
    ax_total.text(
        0.5, 0.40, f"${total_sales/1_000_000_000:.2f}B",
        ha="center", fontsize=20, fontweight="bold"
    )
    add_black_square(ax_total, aspect=1.10)
    
    chart_data.plot(kind="bar", ax=ax_bar,  width=0.95)
    ax_bar.yaxis.set_major_formatter(millions)
    ax_bar.set_title(f"Total weekly sales by store: {min_date} to {max_date}")
    ax_bar.set_ylabel("Weekly Sales")
    ax_bar.set_xlabel("Store ID")
    ax_bar.legend(
        title = "Is Holiday:",
        ncol = 1
    )

    ax_bar.grid(alpha=0.3)

    for container in ax_bar.containers:
        labels = [millions(value) for value in container.datavalues]
        ax_bar.bar_label(container, labels=labels, padding=3, fontsize=8)

    ax_bar.margins(y=0.12)


    save(fig, "01_weekly_sales_by_store.png")



def draw_sales_by_size(ax, store):
    plot_data = store.sort_values("STORE_SIZE")
    x = plot_data["STORE_SIZE"]
    y = plot_data["WEEKLY_SALES"]

    ax.fill_between(x, y, color="cornflowerblue", alpha=0.4)
    ax.plot(x, y, color="dodgerblue", linewidth=1.5)
    ax.set_title("Sales by Store Size")
    ax.set_xlabel("Store Size")
    ax.set_ylabel("Weekly Sales")
    ax.grid(alpha=0.3)


def weekly_sales_by_store_size(sw):
    store = (
        sw.groupby(["STORE_ID", "STORE_SIZE"], as_index=False)["WEEKLY_SALES"]
        .sum()
    )

    # Interactive Streamlit chart and table
    fig, ax = plt.subplots(figsize=(12, 6))
    draw_sales_by_size(ax, store)

    chart_col, table_col = st.columns([3, 2], gap="medium")

    with chart_col:
        st.pyplot(fig, width="stretch")

    with table_col:
        st.subheader("Store Sales")
        st.dataframe(
            store.sort_values("WEEKLY_SALES", ascending=False)[
                ["STORE_ID", "STORE_SIZE", "WEEKLY_SALES"]
            ],
            width="stretch",
            height=560,
            hide_index=True,
        )

    plt.close(fig)

    # Static PNG with chart and every store in the table
    table_data = store.sort_values("WEEKLY_SALES", ascending=False)
    fig_height = max(12, 0.34 * (len(table_data) + 1))

    png_fig, (ax_chart, ax_table) = plt.subplots(
        1,
        2,
        figsize=(20, fig_height),
        gridspec_kw={"width_ratios": [2.2, 1]},
    )

    draw_sales_by_size(ax_chart, store)

    rows = [
        [
            str(row.STORE_ID),
            f"{row.STORE_SIZE:,.0f}",
            f"${row.WEEKLY_SALES:,.2f}",
        ]
        for row in table_data.itertuples(index=False)
    ]

    ax_table.axis("off")
    ax_table.set_title("Store Sales")

    table = ax_table.table(
        cellText=rows,
        colLabels=["Store ID", "Size", "Weekly Sales"],
        colWidths=[0.20, 0.24, 0.56],
        cellLoc="right",
        bbox=[0, 0, 1, 0.96],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)

    save(png_fig, "03_sales_by_store_size.png")    

from matplotlib.patches import Patch


def chart_weekly_sales_waterfall(sw):
    data = sw.copy()
    data["STORE_DATE"] = pd.to_datetime(data["STORE_DATE"])
    data["WEEKLY_SALES"] = pd.to_numeric(
        data["WEEKLY_SALES"], errors="coerce"
    )

    store_ids = sorted(data["STORE_ID"].dropna().unique())
    selected_store = st.selectbox("Select Store", store_ids)

    # Get one sales value per week for the selected store
    weekly = (
        data[data["STORE_ID"] == selected_store]
        .groupby("STORE_DATE", as_index=False)["WEEKLY_SALES"]
        .sum()
        .sort_values("STORE_DATE")
        .dropna(subset=["WEEKLY_SALES"])
    )

    if weekly.empty:
        st.warning("No weekly sales data for this store.")
        return

    sales = weekly["WEEKLY_SALES"].to_numpy()
    dates = weekly["STORE_DATE"].dt.strftime("%m/%d/%y").tolist()

    increase_color = "deepskyblue"
    decrease_color = "dimgray"
    start_color = "gold"
    total_color = "darkslategray"

    x_positions = []
    bottoms = []
    heights = []
    colors = []
    labels = []
    categories = []

    # First week's sales: starting value
    x_positions.append(0)
    bottoms.append(0)
    heights.append(sales[0])
    colors.append(start_color)
    labels.append(f"{sales[0] / 1e6:.2f}M")
    categories.append(dates[0])

    running_total = sales[0]

    # Following bars: week-to-week changes
    for i in range(1, len(sales)):
        change = sales[i] - sales[i - 1]

        x_positions.append(i)
        bottoms.append(running_total if change >= 0 else running_total + change)
        heights.append(abs(change))
        colors.append(increase_color if change >= 0 else decrease_color)
        labels.append(f"{change / 1e6:+.2f}M")
        categories.append(dates[i])

        running_total += change

    # Final bar: ending week's sales
    x_positions.append(len(sales))
    bottoms.append(0)
    heights.append(sales[-1])
    colors.append(total_color)
    labels.append(f"{sales[-1] / 1e6:.2f}M")
    categories.append("Ending Sales")

    fig_width = max(14, len(categories) * 0.3)
    fig, ax = plt.subplots(figsize=(fig_width, 7))

    bars = ax.bar(
        x_positions,
        heights,
        bottom=bottoms,
        color=colors,
        width=0.7,
    )

    for bar, label in zip(bars, labels):
        y = bar.get_y() + bar.get_height()
        ax.annotate(
            label,
            (bar.get_x() + bar.get_width() / 2, y),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )

    ax.set_title(f"Weekly Sales Waterfall — Store {selected_store}")
    ax.set_xlabel("Week")
    ax.set_ylabel("Weekly Sales")
    ax.set_xticks(x_positions, categories, rotation=90)
    ax.yaxis.set_major_formatter(
        lambda value, position: f"{value / 1e6:.1f}M"
    )
    ax.grid(axis="y", alpha=0.3)

    ax.legend(
        handles=[
            Patch(color=increase_color, label="Increase"),
            Patch(color=decrease_color, label="Decrease"),
            Patch(color=start_color, label="Starting Sales"),
            Patch(color=total_color, label="Ending Sales"),
        ],
        loc="upper left",
        ncol=4,
    )

    st.pyplot(fig, width="stretch")
    save(fig, f"02_weekly_sales_waterfall_store_{selected_store}.png")



def weekly_sales_by_store_type_and_month(sw):
    data = sw.copy()
    data["STORE_DATE"] = pd.to_datetime(data["STORE_DATE"])
    data["WEEKLY_SALES"] = pd.to_numeric(
        data["WEEKLY_SALES"], errors="coerce"
    )
    data["STORE_TYPE"] = data["STORE_TYPE"].astype(str)

    data["MONTH_NUM"] = data["STORE_DATE"].dt.month

    store_types = sorted(data["STORE_TYPE"].dropna().unique())

    # One total per month and store type
    monthly = (
        data.groupby(["MONTH_NUM", "STORE_TYPE"])["WEEKLY_SALES"]
        .sum()
        .unstack("STORE_TYPE")
        .reindex(index=range(1, 13), columns=store_types, fill_value=0)
        .fillna(0)
    )

    month_names = [calendar.month_name[m] for m in range(1, 13)]

    def draw_chart(ax):
        x = np.arange(12)

        for store_type in store_types:
            y = monthly[store_type].to_numpy()

            ax.plot(x, y, linewidth=1.5, label=store_type)

            # Label each month's value in millions
            for month_index, value in enumerate(y):
                ax.annotate(
                    f"{value / 1_000_000:.0f}M",
                    (month_index, value),
                    textcoords="offset points",
                    xytext=(0, 7),
                    ha="center",
                    fontsize=8,
                )

        ax.set_title("Weekly Sales by Store Type and Month")
        ax.set_xlabel("Month")
        ax.set_ylabel("Weekly Sales")
        ax.set_xticks(x, month_names)
        ax.yaxis.set_major_formatter(
            lambda value, position: f"{value / 1_000_000:.0f}M"
        )
        ax.legend(title="Store Type")
        ax.grid(alpha=0.3)

    # Streamlit view: chart beside an interactive table
    chart_fig, chart_ax = plt.subplots(figsize=(12, 6))
    draw_chart(chart_ax)

    chart_col, table_col = st.columns([3, 2], gap="medium")

    with chart_col:
        st.pyplot(chart_fig, width="stretch")

    with table_col:
        st.subheader("Monthly Sales by Store Type")

        interactive_table = monthly.copy()
        interactive_table.insert(0, "Month", month_names)

        total_row = {"Month": "Total"}
        total_row.update(monthly.sum().to_dict())

        interactive_table = pd.concat(
            [interactive_table, pd.DataFrame([total_row])],
            ignore_index=True,
        )

        st.dataframe(
            interactive_table,
            width="stretch",
            height=560,
            hide_index=True,
        )

    plt.close(chart_fig)

    # PNG view: chart and a static table together
    export_fig, (export_ax, table_ax) = plt.subplots(
        1,
        2,
        figsize=(20, 9),
        gridspec_kw={"width_ratios": [2.2, 1]},
    )

    draw_chart(export_ax)

    table_rows = [
        [
            calendar.month_name[month_num],
            *[
                f"${monthly.loc[month_num, store_type]:,.2f}"
                for store_type in store_types
            ],
        ]
        for month_num in range(1, 13)
    ]

    table_rows.append(
        [
            "Total",
            *[
                f"${monthly[store_type].sum():,.2f}"
                for store_type in store_types
            ],
        ]
    )

    table_ax.axis("off")
    table_ax.set_title("Monthly Sales by Store Type")

    table = table_ax.table(
        cellText=table_rows,
        colLabels=["Month", *store_types],
        cellLoc="right",
        bbox=[0, 0, 1, 1],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)

    save(export_fig, "04_weekly_sales_by_store_type_and_month.png")

st.set_page_config(layout="wide")

def markdown_sales_by_year(sw):
    markdown_cols = [
        "MARKDOWN1",
        "MARKDOWN2",
        "MARKDOWN3",
        "MARKDOWN4",
        "MARKDOWN5",
    ]

    data = sw.copy()
    data["STORE_DATE"] = pd.to_datetime(data["STORE_DATE"])

    for col in markdown_cols:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

    data["YEAR"] = data["STORE_DATE"].dt.year

    # Sum markdown sales across stores for each year
    yearly_totals = (
        data.groupby("YEAR")[markdown_cols]
        .sum()
        .sort_index()
    )

    years = yearly_totals.index.tolist()

    # Table: select a year and show its totals by store
    table_col, chart_col = st.columns([1.2, 1.8], gap="medium")

    with table_col:
        selected_year = st.selectbox(
            "Select year for markdown sales",
            years,
            index=len(years) - 1,
        )

        store_table = (
            data[data["YEAR"] == selected_year]
            .groupby("STORE_ID", as_index=False)[markdown_cols]
            .sum()
            .sort_values("STORE_ID")
        )

        total_row = {"STORE_ID": "Total"}
        total_row.update(store_table[markdown_cols].sum().to_dict())

        store_table = pd.concat(
            [store_table, pd.DataFrame([total_row])],
            ignore_index=True,
        )

        store_table["STORE_ID"] = store_table["STORE_ID"].astype("string")

        st.dataframe(
            store_table,
            width="stretch",
            height=460,
            hide_index=True,
        )

    # Grouped bar chart: one bar per markdown type for each year
    with chart_col:
        fig, ax = plt.subplots(figsize=(12, 7))

        x = np.arange(len(years))
        bar_width = 0.15

        for i, col in enumerate(markdown_cols):
            offset = (i - (len(markdown_cols) - 1) / 2) * bar_width
            values = yearly_totals[col].to_numpy()

            bars = ax.bar(
                x + offset,
                values,
                width=bar_width,
                label=col,
            )

            labels = [f"{value / 1e9:.3f}bn" for value in values]
            ax.bar_label(
                bars,
                labels=labels,
                padding=2,
                fontsize=7,
            )

        ax.set_title("Markdown Sales by Year")
        ax.set_xlabel("Year")
        ax.set_ylabel("Markdown Sales")
        ax.set_xticks(x, years)
        ax.yaxis.set_major_formatter(
            lambda value, position: f"{value / 1e9:.1f}bn"
        )
        ax.legend(title="Markdown")
        ax.grid(axis="y", alpha=0.3)

        st.pyplot(fig, width="stretch")
        save(fig, "05_markdown_sales_by_year.png")

from matplotlib.patches import Patch


def weekly_sales_by_store_type(sw):
    data = sw.copy()
    data["WEEKLY_SALES"] = pd.to_numeric(
        data["WEEKLY_SALES"], errors="coerce"
    ).fillna(0)

    # Sum weekly sales across dates, producing one total per store
    store_sales = (
        data.groupby(["STORE_TYPE", "STORE_ID"], as_index=False)["WEEKLY_SALES"]
        .sum()
    )

    types = sorted(store_sales["STORE_TYPE"].dropna().unique())

    selected_types = st.multiselect(
        "Select store type",
        options=types,
        default=types,
    )

    if not selected_types:
        st.info("Select at least one store type.")
        return

    filtered = store_sales[
        store_sales["STORE_TYPE"].isin(selected_types)
    ]

    type_totals = (
        filtered.groupby("STORE_TYPE")["WEEKLY_SALES"]
        .sum()
        .reindex(selected_types, fill_value=0)
    )

    type_colors = {
        "A": "cornflowerblue",
        "B": "darkslategray",
        "C": "salmon",
    }

    store_ids = sorted(filtered["STORE_ID"].unique())
    store_colors = dict(
        zip(
            store_ids,
            plt.cm.turbo(np.linspace(0, 1, max(len(store_ids), 1))),
        )
    )

    chart_height = max(8, 0.22 * len(filtered))

    fig, (ax_pie, ax_bar) = plt.subplots(
        1,
        2,
        figsize=(18, chart_height),
        gridspec_kw={"width_ratios": [1, 2.3]},
    )

    # Pie chart: sales share by store type
    pie_colors = [
        type_colors.get(store_type, "gray")
        for store_type in type_totals.index
    ]

    ax_pie.pie(
        type_totals.values,
        labels=type_totals.index,
        colors=pie_colors,
        startangle=90,
    )
    ax_pie.set_title("Weekly Sales by Store Type")
    ax_pie.axis("equal")

    # Horizontal bars grouped by store type, colored by store ID
    y_positions = []
    type_centers = []
    type_labels = []
    current_y = 0

    for store_type in selected_types:
        group = (
            filtered[filtered["STORE_TYPE"] == store_type]
            .sort_values("STORE_ID")
        )

        group_positions = []

        for row in group.itertuples(index=False):
            y = current_y
            sales = row.WEEKLY_SALES

            ax_bar.barh(
                y,
                sales,
                color=store_colors[row.STORE_ID],
                height=0.75,
            )
            ax_bar.text(
                sales,
                y,
                f"  {sales / 1_000_000:.0f}M",
                va="center",
                fontsize=7,
            )

            y_positions.append(y)
            group_positions.append(y)
            current_y += 1

        if group_positions:
            type_centers.append(
                sum(group_positions) / len(group_positions)
            )
            type_labels.append(store_type)
            current_y += 1  # gap between store-type groups

    ax_bar.set_yticks(type_centers, type_labels)
    ax_bar.invert_yaxis()
    ax_bar.set_title("Weekly Sales by Store and Type")
    ax_bar.set_xlabel("Weekly Sales")
    ax_bar.xaxis.set_major_formatter(
        lambda value, position: f"{value / 1_000_000:.0f}M"
    )
    ax_bar.grid(axis="x", alpha=0.3)

    legend_handles = [
        Patch(color=store_colors[store_id], label=str(store_id))
        for store_id in store_ids
    ]

    ax_bar.legend(
        handles=legend_handles,
        title="Store ID",
        loc="lower left",
        bbox_to_anchor=(0, 1.01),
        ncol=min(8, len(legend_handles)),
        fontsize=7,
    )

    st.pyplot(fig, width="stretch")
    save(fig, "06_weekly_sales_by_store_type.png")

def fuel_price_by_year(sw):
    data = sw.copy()
    data["STORE_DATE"] = pd.to_datetime(data["STORE_DATE"])
    data["FUEL_PRICE"] = pd.to_numeric(data["FUEL_PRICE"], errors="coerce")
    data = data.dropna(subset=["STORE_ID", "STORE_DATE", "FUEL_PRICE"])
    data["YEAR"] = data["STORE_DATE"].dt.year

    years = sorted(data["YEAR"].unique())

    # Store rows; year columns
    store_year = data.pivot_table(
        index="STORE_ID",
        columns="YEAR",
        values="FUEL_PRICE",
        aggfunc="sum",
        fill_value=0,
    ).reindex(columns=years, fill_value=0)

    store_year["Total"] = store_year.sum(axis=1)
    store_year.loc["Total"] = store_year.sum(numeric_only=True)
    store_year.index.name = "STORE_ID"

    table_data = store_year.reset_index()
    # Make the Store ID column consistently text so Arrow can display "Total".
    table_data["STORE_ID"] = table_data["STORE_ID"].astype("string")

    # Year totals for the donut and overall total for the card
    yearly_fuel = data.groupby("YEAR")["FUEL_PRICE"].sum().reindex(years)
    total_fuel = data["FUEL_PRICE"].sum()

    # Interactive Streamlit layout
    table_col, chart_col = st.columns([1.5, 1])

    with table_col:
        st.dataframe(
            table_data,
            width="stretch",
            height=560,
            hide_index=True,
        )

    with chart_col:
        chart_fig = plt.figure(figsize=(6, 7))
        grid = chart_fig.add_gridspec(2, 1, height_ratios=[1.2, 0.8])
        ax_donut = chart_fig.add_subplot(grid[0])
        ax_total = chart_fig.add_subplot(grid[1])

        ax_donut.pie(
            yearly_fuel.values,
            labels=[str(year) for year in years],
            startangle=90,
            wedgeprops={"width": 0.45},
        )
        ax_donut.set_title("Fuel Price by Year")
        ax_donut.axis("equal")

        ax_total.axis("off")
        ax_total.text(
            0.5, 0.58, f"{total_fuel / 1_000_000:.2f}M",
            ha="center", va="center", fontsize=24,
        )
        ax_total.text(
            0.5, 0.38, "Fuel_Price",
            ha="center", va="center", fontsize=12,
        )

        st.pyplot(chart_fig, width="stretch")
        plt.close(chart_fig)

    # Static PNG of the full dashboard: table, donut, and total card
    png_fig = plt.figure(figsize=(16, 9))
    grid = png_fig.add_gridspec(
        2, 2,
        width_ratios=[1.5, 1],
        height_ratios=[1.2, 0.8],
    )

    ax_table = png_fig.add_subplot(grid[:, 0])
    ax_donut = png_fig.add_subplot(grid[0, 1])
    ax_total = png_fig.add_subplot(grid[1, 1])

    display_rows = []
    for row in table_data.itertuples(index=False, name=None):
        display_rows.append([
            str(row[0]),
            *[f"{value:,.2f}" for value in row[1:]],
        ])

    ax_table.axis("off")
    ax_table.set_title("Fuel Price by Store and Year")

    table = ax_table.table(
        cellText=display_rows,
        colLabels=["Store"] + [str(year) for year in years] + ["Total"],
        cellLoc="right",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(1, 1.25)

    ax_donut.pie(
        yearly_fuel.values,
        labels=[str(year) for year in years],
        startangle=90,
        wedgeprops={"width": 0.45},
    )
    ax_donut.set_title("Fuel Price by Year")
    ax_donut.axis("equal")

    ax_total.axis("off")
    ax_total.text(
        0.5, 0.58, f"{total_fuel / 1_000_000:.2f}M",
        ha="center", va="center", fontsize=24,
    )
    ax_total.text(
        0.5, 0.38, "Fuel_Price",
        ha="center", va="center", fontsize=12,
    )

    save(png_fig, "07_fuel_price_by_year.png")

def weekly_sales_by_year_month_day(sw):
    data = sw.copy()
    data["STORE_DATE"] = pd.to_datetime(data["STORE_DATE"])
    data["WEEKLY_SALES"] = pd.to_numeric(
        data["WEEKLY_SALES"], errors="coerce"
    )
    data = data.dropna(subset=["STORE_DATE", "WEEKLY_SALES"])

    data["YEAR"] = data["STORE_DATE"].dt.year
    data["MONTH_NUM"] = data["STORE_DATE"].dt.month
    data["DAY"] = data["STORE_DATE"].dt.day

    # Sum sales by year
    sales_by_year = data.groupby("YEAR")["WEEKLY_SALES"].sum().sort_index()

    # Sum sales by month across all years
    sales_by_month = (
        data.groupby("MONTH_NUM")["WEEKLY_SALES"]
        .sum()
        .reindex(range(1, 13), fill_value=0)
    )
    month_names = [
        calendar.month_name[month] for month in range(1, 13)
    ]

    # Sum sales by calendar day of the month across all years
    sales_by_day = (
        data.groupby("DAY")["WEEKLY_SALES"]
        .sum()
        .reindex(range(1, 32), fill_value=0)
    )

    fig = plt.figure(figsize=(16, 10))
    grid = fig.add_gridspec(
        2, 2,
        height_ratios=[1, 1.1],
        width_ratios=[1, 1.6],
    )

    ax_year = fig.add_subplot(grid[0, 0])
    ax_month = fig.add_subplot(grid[0, 1])
    ax_day = fig.add_subplot(grid[1, :])

    def add_value_labels(ax, bars, values, formatter):
        max_value = max(values) if len(values) else 0

        for bar, value in zip(bars, values):
            ax.annotate(
                formatter(value),
                (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                fontsize=8,
            )

        if max_value > 0:
            ax.set_ylim(0, max_value * 1.15)

    # Year chart
    year_bars = ax_year.bar(
        sales_by_year.index.astype(str),
        sales_by_year.values,
        color="deepskyblue",
    )
    ax_year.set_title("Weekly Sales by Year")
    ax_year.set_ylabel("Weekly Sales")
    ax_year.yaxis.set_major_formatter(
        lambda value, position: f"{value / 1e9:.1f}bn"
    )
    add_value_labels(
        ax_year,
        year_bars,
        sales_by_year.values,
        lambda value: f"{value / 1e9:.2f}bn",
    )
    ax_year.grid(axis="y", alpha=0.3)

    # Month chart, summed across all years
    month_bars = ax_month.bar(
        month_names,
        sales_by_month.values,
        color="deepskyblue",
    )
    ax_month.set_title("Weekly Sales by Month")
    ax_month.set_ylabel("Weekly Sales")
    ax_month.tick_params(axis="x", rotation=35)
    ax_month.yaxis.set_major_formatter(
        lambda value, position: f"{value / 1e9:.1f}bn"
    )
    add_value_labels(
        ax_month,
        month_bars,
        sales_by_month.values,
        lambda value: f"{value / 1e9:.2f}bn",
    )
    ax_month.grid(axis="y", alpha=0.3)

    # Day-of-month chart, summed across all years
    day_bars = ax_day.bar(
        sales_by_day.index,
        sales_by_day.values,
        color="deepskyblue",
    )
    ax_day.set_title("Weekly Sales by Day of Month")
    ax_day.set_xlabel("Day of Month")
    ax_day.set_ylabel("Weekly Sales")
    ax_day.set_xticks(range(1, 32))
    ax_day.yaxis.set_major_formatter(
        lambda value, position: f"{value / 1e6:.0f}M"
    )
    add_value_labels(
        ax_day,
        day_bars,
        sales_by_day.values,
        lambda value: f"{value / 1e6:.0f}M",
    )
    ax_day.grid(axis="y", alpha=0.3)

    st.pyplot(fig, width="stretch")
    save(fig, "08_weekly_sales_by_year_month_day.png")

def weekly_sales_by_cpi(sw):
    data = sw.copy()
    data["CPI"] = pd.to_numeric(data["CPI"], errors="coerce")
    data["WEEKLY_SALES"] = pd.to_numeric(
        data["WEEKLY_SALES"], errors="coerce"
    )
    data = data.dropna(subset=["CPI", "WEEKLY_SALES"])

    fig, ax = plt.subplots(figsize=(14, 7))

    ax.scatter(
        data["CPI"],
        data["WEEKLY_SALES"],
        color="dodgerblue",
        s=12,
        alpha=0.45,
    )

    ax.set_title("Weekly Sales by CPI")
    ax.set_xlabel("CPI")
    ax.set_ylabel("Weekly Sales")
    ax.yaxis.set_major_formatter(
        lambda value, position: f"{value / 1_000_000:.0f}M"
    )
    ax.grid(alpha=0.3)

    st.pyplot(fig, width="stretch")
    save(fig, "09_weekly_sales_by_cpi.png")

def department_weekly_sales(dept):
    data = dept.copy()

    # Normalize column names and ensure sales are numeric
    data.columns = data.columns.str.upper()
    data["WEEKLY_SALES"] = pd.to_numeric(
        data["WEEKLY_SALES"], errors="coerce"
    )
    data = data.dropna(subset=["DEPT_ID", "WEEKLY_SALES"])

    # Sum sales across all stores and dates for each department
    department_totals = (
        data.groupby("DEPT_ID", as_index=False)["WEEKLY_SALES"]
        .sum()
        .sort_values("DEPT_ID")
    )

    total_sales = department_totals["WEEKLY_SALES"].sum()

    top_five = (
        department_totals
        .nlargest(5, "WEEKLY_SALES")
        .sort_values("WEEKLY_SALES", ascending=False)
    )

    # Dashboard heading
    st.title("Department-Wise Weekly Sales")

    # Top row: sortable department table, total sales KPI, top five table
    table_col, total_col, top_col = st.columns([1.2, 1, 1.2])

    with table_col:
        st.subheader("Sales by Department")
        st.dataframe(
            department_totals,
            width="stretch",
            height=230,
            hide_index=True,
            column_config={
                "DEPT_ID": st.column_config.NumberColumn("Department"),
                "WEEKLY_SALES": st.column_config.NumberColumn(
                    "Weekly Sales",
                    format="$%,.2f",
                ),
            },
        )
        # Click either column heading to sort by department or sales.

    with total_col:
        st.subheader("Total Sales")
        st.metric(
            label="Weekly Sales",
            value=f"${total_sales / 1e9:.3f}bn",
        )

    with top_col:
        st.subheader("Top 5 Departments by Sales")
        st.dataframe(
            top_five,
            width="stretch",
            height=230,
            hide_index=True,
            column_config={
                "DEPT_ID": st.column_config.NumberColumn("Department"),
                "WEEKLY_SALES": st.column_config.NumberColumn(
                    "Weekly Sales",
                    format="$%,.2f",
                ),
            },
        )

    # Bottom chart: department on x-axis, total sales on y-axis
    fig, ax = plt.subplots(figsize=(16, 6))

    x = np.arange(len(department_totals))
    sales = department_totals["WEEKLY_SALES"]

    ax.bar(x, sales, color="cornflowerblue", width=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(department_totals["DEPT_ID"].astype(str))
    ax.set_title("Total Weekly Sales by Department")
    ax.set_xlabel("Department")
    ax.set_ylabel("Weekly Sales")
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda value, _: f"${value / 1e9:.1f}bn")
    )
    ax.grid(axis="y", alpha=0.3)

    st.pyplot(fig, width="stretch")
    save(fig, "10_department_wise_weekly_sales.png")

# ---------------------------------------------------------------------------
def main():
    conn = connect()
    try:
        sw = query(conn, STORE_WEEK_SQL)
        dept = query(conn, DEPT_SQL)
    finally:
        conn.close()

    sw["STORE_DATE"] = pd.to_datetime(sw["STORE_DATE"])
    sw["ISHOLIDAY"] = sw["ISHOLIDAY"].astype(str).str.upper().isin(["TRUE", "1"])
    sw["WEEKLY_SALES"] = pd.to_numeric(sw["WEEKLY_SALES"], errors="coerce")

    chart_sales_by_store(sw)
    chart_weekly_sales_waterfall(sw)
    weekly_sales_by_store_size(sw)
    weekly_sales_by_store_type_and_month(sw)
    markdown_sales_by_year(sw)
    weekly_sales_by_store_type(sw)
    fuel_price_by_year(sw)
    weekly_sales_by_year_month_day(sw)
    weekly_sales_by_cpi(sw)
    department_weekly_sales(dept)


if __name__ == "__main__":
    main()