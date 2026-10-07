import os
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Coil Slip Analytics",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_FILE = "coil_slip_file.xlsx"

st.markdown(
    """
    <style>
    .stApp {
        background: #0b1220;
        color: #e6edf7;
    }
    [data-testid="stHeader"] {
        background: rgba(11, 18, 32, 0.88);
    }
    [data-testid="stSidebar"] {
        background: #0e1828;
    }
    [data-testid="stSidebar"] * {
        color: #e6edf7;
    }
    .block-container {
        max-width: 1600px;
        padding-top: 2rem;
        padding-bottom: 2.5rem;
    }
    .dashboard-hero {
        padding: 1.6rem 1.9rem;
        margin-bottom: 1.4rem;
        border: 1px solid #26364d;
        border-radius: 18px;
        background: linear-gradient(115deg, #17253b 0%, #111c2e 100%);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.2);
    }
    .dashboard-hero h1 {
        margin: 0;
        color: #f3f7fc;
        font-size: 2rem;
        letter-spacing: -0.035em;
    }
    .dashboard-hero p {
        margin: 0.45rem 0 0;
        color: #a9bad0;
        font-size: 0.98rem;
    }
    [data-testid="stMetric"] {
        min-height: 112px;
        padding: 1rem 1.1rem;
        border: 1px solid #26364d;
        border-radius: 14px;
        background: #111c2e;
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.16);
    }
    [data-testid="stMetricLabel"] {
        color: #a9bad0;
        font-weight: 600;
    }
    [data-testid="stMetricValue"] {
        color: #f3f7fc;
        font-weight: 700;
    }
    [data-testid="stPlotlyChart"],
    [data-testid="stDataFrame"] {
        border: 1px solid #26364d;
        border-radius: 14px;
        background: #111c2e;
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.12);
        overflow: hidden;
    }
    h2, h3 {
        color: #edf3fb;
        letter-spacing: -0.02em;
    }
    [data-testid="stCaptionContainer"] {
        color: #9aacc3;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data(file_source):
    df = pd.read_excel(file_source, sheet_name="Sheet1", skiprows=3)
    df = df.iloc[:, :8].copy()
    df.columns = [
        "Date", "Total Size", "Weight", "Seera",
        "Side Cutting", "Coil", "Scrap", "Total Weight"
    ]

    # Keep source values intact; parsed date is only for filtering/trends.
    df["Analysis Date"] = pd.to_datetime(
        df["Date"], dayfirst=True, errors="coerce"
    )

    numeric_cols = [
        "Total Size", "Weight", "Seera",
        "Side Cutting", "Scrap", "Total Weight"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Scrap %"] = np.where(
        df["Total Weight"].ne(0),
        df["Scrap"] / df["Total Weight"] * 100,
        np.nan
    )

    df["Month"] = df["Analysis Date"].dt.to_period("M").astype(str)

    # Validation only; source workbook is not modified.
    df["Calculated Total"] = df["Weight"] + df["Scrap"]
    df["Weight Check Difference"] = (
        df["Total Weight"] - df["Calculated Total"]
    )

    return df


def fmt_num(value):
    if pd.isna(value):
        return "-"
    return f"{value:,.0f}"


def style_chart(fig, height=380):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor="#111c2e",
        plot_bgcolor="#111c2e",
        font=dict(family="Arial, sans-serif", color="#d6e0ee", size=12),
        margin=dict(l=24, r=24, t=52, b=24),
        title=dict(font=dict(size=16, color="#edf3fb")),
        hoverlabel=dict(bgcolor="#1d2d45", font_color="#ffffff"),
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor="#344760",
        tickfont=dict(color="#a9bad0"),
        title_font=dict(color="#c6d3e3"),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#26364d",
        zeroline=False,
        tickfont=dict(color="#a9bad0"),
        title_font=dict(color="#c6d3e3"),
    )
    return fig


st.markdown(
    """
    <div class="dashboard-hero">
      <h1>Coil Slip Analytics</h1>
      <p>Production overview &nbsp;·&nbsp; Coil slip register &nbsp;·&nbsp;
      All figures are calculated from the source workbook</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------- DATA SOURCE --------------------
with st.sidebar:
    st.header("📂 Data Source")

    if os.path.exists(DEFAULT_FILE):
        source = DEFAULT_FILE
        st.success(f"Using: {DEFAULT_FILE}")
    else:
        uploaded = st.file_uploader(
            "Upload Coil Slip Excel file",
            type=["xlsx", "xls"]
        )
        if uploaded is None:
            st.info("Upload the coil slip Excel file to start.")
            st.stop()
        source = uploaded

df = load_data(source)

# -------------------- SIDEBAR FILTERS --------------------
with st.sidebar:
    st.header("🔎 Filters")

    valid_dates = df["Analysis Date"].dropna()
    if not valid_dates.empty:
        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()

        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date = end_date = date_range
    else:
        start_date = end_date = None

    coil_options = sorted(df["Coil"].dropna().astype(str).unique().tolist())
    selected_coils = st.multiselect(
        "Coil Type",
        coil_options,
        default=coil_options
    )

    size_options = sorted(
        df["Total Size"].dropna().unique().tolist()
    )
    selected_sizes = st.multiselect(
        "Total Size",
        size_options,
        default=size_options
    )

filtered = df.copy()

if start_date is not None and end_date is not None:
    filtered = filtered[
        filtered["Analysis Date"].dt.date.between(start_date, end_date)
    ]

if selected_coils:
    filtered = filtered[
        filtered["Coil"].astype(str).isin(selected_coils)
    ]

if selected_sizes:
    filtered = filtered[
        filtered["Total Size"].isin(selected_sizes)
    ]

# -------------------- KPI CALCULATIONS --------------------
records = len(filtered)
weight = filtered["Weight"].sum()
scrap = filtered["Scrap"].sum()
total_weight = filtered["Total Weight"].sum()
scrap_pct = (scrap / total_weight * 100) if total_weight else 0

st.subheader("Key performance indicators")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Slip records", f"{records:,}")
c2.metric("Weight (kg)", f"{fmt_num(weight)} kg")
c3.metric("Scrap (kg)", f"{fmt_num(scrap)} kg")
c4.metric("Total weight (kg)", f"{fmt_num(total_weight)} kg")
c5.metric("Scrap rate", f"{scrap_pct:.2f}%")

st.divider()

# -------------------- DATA QUALITY --------------------
with st.expander("🧪 Data Quality & Validation"):
    col_a, col_b, col_c = st.columns(3)

    missing_count = int(filtered.isna().sum().sum())
    duplicate_count = int(filtered.duplicated().sum())
    incorrect_total = int(
        (filtered["Weight Check Difference"].abs() > 0.0001).sum()
    )

    col_a.metric("Missing Cells", f"{missing_count:,}")
    col_b.metric("Duplicate Rows", f"{duplicate_count:,}")
    col_c.metric("Weight Calculation Errors", f"{incorrect_total:,}")

    st.write(
        "**Validation:** `Total Weight` is checked against `Weight + Scrap`. "
        "The source Excel file is not modified."
    )

# -------------------- CHART 1: MONTHLY --------------------
st.subheader("Monthly production & scrap trend")

monthly = (
    filtered.dropna(subset=["Analysis Date"])
    .assign(Month=filtered.dropna(subset=["Analysis Date"])["Analysis Date"].dt.to_period("M").astype(str))
    .groupby("Month", as_index=False)
    .agg(
        Records=("Month", "size"),
        Weight=("Weight", "sum"),
        Scrap=("Scrap", "sum"),
        Total_Weight=("Total Weight", "sum"),
    )
)

if not monthly.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly["Month"], y=monthly["Total_Weight"],
        mode="lines+markers", name="Total weight (kg)",
        line=dict(color="#2473b8", width=3),
        marker=dict(size=7),
    ))
    fig.add_trace(go.Scatter(
        x=monthly["Month"], y=monthly["Scrap"],
        mode="lines+markers", name="Scrap (kg)",
        line=dict(color="#e28b45", width=3),
        marker=dict(size=7),
    ))
    style_chart(fig, height=400)
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Weight (kg)",
        hovermode="x unified",
        legend_title="",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No valid date records available for the selected filters.")

# -------------------- TWO-COLUMN ANALYSIS --------------------
left, right = st.columns(2)

with left:
    st.subheader("Coil type analysis")

    coil_summary = (
        filtered.groupby("Coil", dropna=False, as_index=False)
        .agg(
            Records=("Coil", "size"),
            Weight=("Weight", "sum"),
            Scrap=("Scrap", "sum"),
            Total_Weight=("Total Weight", "sum")
        )
    )
    coil_summary["Scrap %"] = np.where(
        coil_summary["Total_Weight"].ne(0),
        coil_summary["Scrap"] / coil_summary["Total_Weight"] * 100,
        np.nan
    )

    if not coil_summary.empty:
        fig = px.bar(
            coil_summary,
            x="Coil",
            y="Total_Weight",
            text_auto=".0f",
            title="Total weight by coil type",
            color_discrete_sequence=["#2473b8"],
        )
        style_chart(fig)
        fig.update_layout(xaxis_title="Coil", yaxis_title="Total weight (kg)")
        st.plotly_chart(fig, use_container_width=True)
        coil_display = coil_summary.sort_values(
            "Total_Weight", ascending=False
        ).rename(columns={
            "Records": "Records",
            "Weight": "Weight (kg)",
            "Scrap": "Scrap (kg)",
            "Total_Weight": "Total weight (kg)",
        })
        st.dataframe(
            coil_display,
            use_container_width=True,
            hide_index=True
        )

with right:
    st.subheader("Total size analysis")

    size_summary = (
        filtered.groupby("Total Size", dropna=False, as_index=False)
        .agg(
            Records=("Total Size", "size"),
            Weight=("Weight", "sum"),
            Scrap=("Scrap", "sum"),
            Total_Weight=("Total Weight", "sum")
        )
    )
    size_summary["Scrap %"] = np.where(
        size_summary["Total_Weight"].ne(0),
        size_summary["Scrap"] / size_summary["Total_Weight"] * 100,
        np.nan
    )

    if not size_summary.empty:
        fig = px.bar(
            size_summary,
            x="Total Size",
            y="Total_Weight",
            text_auto=".0f",
            title="Total weight by size",
            color_discrete_sequence=["#2d9b8c"],
        )
        style_chart(fig)
        fig.update_layout(xaxis_title="Total size", yaxis_title="Total weight (kg)")
        st.plotly_chart(fig, use_container_width=True)
        size_display = size_summary.sort_values(
            "Total_Weight", ascending=False
        ).rename(columns={
            "Records": "Records",
            "Weight": "Weight (kg)",
            "Scrap": "Scrap (kg)",
            "Total_Weight": "Total weight (kg)",
        })
        st.dataframe(
            size_display,
            use_container_width=True,
            hide_index=True
        )

# -------------------- SCRAP ANALYSIS --------------------
st.subheader("Scrap analysis")

s1, s2 = st.columns(2)

with s1:
    scrap_components = pd.DataFrame({
        "Component": ["Seera", "Side Cutting"],
        "Amount": [
            filtered["Seera"].sum(skipna=True),
            filtered["Side Cutting"].sum(skipna=True)
        ]
    })

    fig = px.bar(
        scrap_components,
        x="Component",
        y="Amount",
        text_auto=".0f",
        title="Scrap component breakdown",
        color="Component",
        color_discrete_sequence=["#e28b45", "#b75b55"],
    )
    style_chart(fig, height=350)
    fig.update_layout(xaxis_title="", yaxis_title="Amount (kg)", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with s2:
    top_scrap = (
        filtered[[
            "Date", "Coil", "Total Size",
            "Weight", "Scrap", "Total Weight", "Scrap %"
        ]]
        .sort_values("Scrap %", ascending=False)
        .head(10)
        .copy()
    )

    if not top_scrap.empty:
        st.markdown("**Top 10 records by scrap rate**")
        # Display date as YYYY-MM-DD without changing the source data.
        top_scrap["Date"] = top_scrap["Date"].apply(
            lambda x: pd.to_datetime(x, dayfirst=True, errors="coerce").strftime("%Y-%m-%d")
            if pd.notna(pd.to_datetime(x, dayfirst=True, errors="coerce"))
            else str(x)
        )
        top_scrap = top_scrap.rename(columns={
            "Weight": "Weight (kg)",
            "Scrap": "Scrap (kg)",
            "Total Weight": "Total weight (kg)",
            "Scrap %": "Scrap rate (%)",
        })
        st.dataframe(
            top_scrap,
            use_container_width=True,
            hide_index=True
        )

# -------------------- DETAIL TABLE --------------------
st.subheader("Filtered coil slip records")

display_df = filtered[[
    "Date", "Total Size", "Weight", "Seera",
    "Side Cutting", "Coil", "Scrap", "Total Weight", "Scrap %"
]].copy()

# Display date without time; source values are not changed.
display_df["Date"] = filtered["Analysis Date"].apply(
    lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "-"
)
display_df = display_df.rename(columns={
    "Weight": "Weight (kg)",
    "Seera": "Seera (kg)",
    "Side Cutting": "Side cutting (kg)",
    "Scrap": "Scrap (kg)",
    "Total Weight": "Total weight (kg)",
    "Scrap %": "Scrap rate (%)",
})

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

# -------------------- FOOTER --------------------
st.caption(
    "Values are shown as recorded in the workbook. Weight fields are displayed in kg; "
    "the source Excel data is never modified."
)
