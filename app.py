import pandas as pd
import plotly.express as px
import streamlit as st

import analysis


st.set_page_config(
    page_title="RentScope | Bengaluru Rental Analytics",
    page_icon="RS",
    layout="wide",
    initial_sidebar_state="expanded",
)


MIN_LOCALITY_LISTINGS = analysis.MIN_LOCALITY_LISTINGS
MIN_COMPARABLE_LISTINGS = analysis.MIN_COMPARABLE_LISTINGS
CHART_HEIGHT = 390


def indian_number(value: float | int) -> str:
    value = int(round(float(value)))
    sign = "-" if value < 0 else ""
    number = str(abs(value))
    if len(number) <= 3:
        return sign + number
    last_three = number[-3:]
    rest = number[:-3]
    groups = []
    while len(rest) > 2:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.insert(0, rest)
    return sign + ",".join(groups + [last_three])


def inr(value: float | int) -> str:
    return f"₹{indian_number(value)}"


def compact_rate(value: float | int) -> str:
    return f"₹{float(value):,.1f}"


def pct(value: float | int) -> str:
    return f"{float(value):+.1f}%"


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --rs-bg: #f6f7f9;
            --rs-panel: #ffffff;
            --rs-ink: #111827;
            --rs-muted: #334155;
            --rs-soft-text: #475569;
            --rs-border: #dfe4ea;
            --rs-accent: #0f766e;
            --rs-accent-soft: #e8f5f3;
        }
        .stApp {
            background: var(--rs-bg);
            color: var(--rs-ink) !important;
        }
        .stApp p,
        .stApp label,
        .stApp span,
        .stApp div[data-testid="stMarkdownContainer"],
        .stApp div[data-testid="stCaptionContainer"],
        .stApp div[data-testid="stWidgetLabel"] {
            color: var(--rs-ink) !important;
        }
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--rs-border);
        }
        [data-testid="stSidebar"],
        [data-testid="stSidebar"] *,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] summary {
            color: var(--rs-ink) !important;
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: var(--rs-ink) !important;
        }
        [data-testid="stSidebar"] div[data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] div[data-testid="stCaptionContainer"] p {
            color: var(--rs-soft-text) !important;
        }
        [data-testid="stSidebar"] svg {
            color: var(--rs-ink) !important;
            fill: currentColor;
        }
        div[role="radiogroup"] label p,
        div[role="radiogroup"] label span {
            color: var(--rs-ink) !important;
            font-weight: 580;
        }
        div[data-baseweb="select"] *,
        div[data-baseweb="popover"] *,
        div[data-baseweb="slider"] *,
        input,
        textarea {
            color: var(--rs-ink) !important;
        }
        span[data-baseweb="tag"] {
            background: var(--rs-accent-soft) !important;
            border: 1px solid #b8ddd7 !important;
            color: var(--rs-ink) !important;
        }
        span[data-baseweb="tag"] * {
            color: var(--rs-ink) !important;
        }
        div[role="slider"] {
            background: #ffffff !important;
            border: 2px solid var(--rs-accent) !important;
            box-shadow: 0 2px 8px rgba(15, 118, 110, 0.18) !important;
            color: var(--rs-ink) !important;
        }
        div[role="slider"] *,
        div[role="slider"] p {
            color: var(--rs-ink) !important;
            font-weight: 650 !important;
        }
        code,
        pre {
            color: var(--rs-ink) !important;
            background: #f1f5f9 !important;
        }
        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2rem;
            max-width: 1420px;
        }
        .page-title {
            font-size: 2rem;
            font-weight: 760;
            letter-spacing: 0;
            margin: 0 0 0.25rem 0;
            color: var(--rs-ink);
        }
        .page-subtitle {
            color: var(--rs-muted) !important;
            font-size: 1rem;
            margin-bottom: 1.2rem;
        }
        .metric-card {
            background: var(--rs-panel);
            border: 1px solid var(--rs-border);
            border-radius: 8px;
            padding: 1rem 1.05rem;
            box-shadow: 0 8px 20px rgba(23, 32, 42, 0.05);
            min-height: 106px;
        }
        .metric-label {
            color: var(--rs-muted);
            font-size: 0.78rem;
            font-weight: 680;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 0.42rem;
        }
        .metric-value {
            color: var(--rs-ink);
            font-size: 1.52rem;
            font-weight: 780;
            line-height: 1.1;
        }
        .metric-note {
            color: var(--rs-soft-text);
            font-size: 0.82rem;
            margin-top: 0.5rem;
        }
        .section-label {
            color: var(--rs-ink);
            font-size: 1.05rem;
            font-weight: 730;
            margin: 0 0 0.7rem 0;
        }
        .info-band {
            background: var(--rs-accent-soft);
            border: 1px solid #b8ddd7;
            color: #0f3f3a !important;
            border-radius: 8px;
            padding: 0.85rem 1rem;
            margin: 0.8rem 0 1rem 0;
        }
        div[data-testid="stMetric"] {
            background: var(--rs-panel);
            border: 1px solid var(--rs-border);
            border-radius: 8px;
            padding: 0.85rem 1rem;
            box-shadow: 0 8px 20px rgba(23, 32, 42, 0.04);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def plotly_layout(fig):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif", color="#111827", size=13),
        margin=dict(l=10, r=10, t=48, b=24),
        hoverlabel=dict(bgcolor="white", bordercolor="#dfe4ea", font=dict(color="#111827", size=12)),
        legend=dict(font=dict(color="#1f2937")),
        legend_title_text="",
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        tickfont=dict(color="#243041"),
        title_font=dict(color="#243041"),
        linecolor="#cbd5e1",
        tickcolor="#64748b",
    )
    fig.update_yaxes(
        gridcolor="#edf0f2",
        zeroline=False,
        tickfont=dict(color="#243041"),
        title_font=dict(color="#243041"),
        linecolor="#cbd5e1",
        tickcolor="#64748b",
    )
    fig.update_coloraxes(
        colorbar=dict(
            tickfont=dict(color="#243041"),
            title=dict(font=dict(color="#243041")),
        )
    )
    return fig


def chart_container(title: str, fig) -> None:
    with st.container(border=True):
        st.markdown(f'<div class="section-label">{title}</div>', unsafe_allow_html=True)
        st.plotly_chart(plotly_layout(fig), width="stretch", config={"displayModeBar": False})


def kpi_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner=False)
def initialize_data_source(data_version: float) -> tuple[str, str | None]:
    try:
        import database

        database.ensure_database_ready()
        return "postgres", None
    except Exception as exc:
        return "csv", str(exc)


@st.cache_data(show_spinner=False)
def load_all_listings(source: str, data_version: float) -> pd.DataFrame:
    if source == "postgres":
        import database

        return database.listings()
    return analysis.load_clean_data()


@st.cache_data(show_spinner=False)
def get_market_data(source: str, data_version: float) -> dict[str, pd.DataFrame | dict[str, float]]:
    if source == "postgres":
        import database

        return {
            "kpis": database.market_kpis().iloc[0].to_dict(),
            "localities": database.locality_metrics(MIN_LOCALITY_LISTINGS),
            "bhk": database.bhk_metrics(),
            "furnishing": database.furnishing_metrics(),
            "availability": database.listing_availability(),
            "distribution": database.rental_distribution(),
            "premium": database.furnishing_premium(),
            "bhk_increment": database.bhk_increment(),
        }

    df = analysis.load_clean_data()
    return {
        "kpis": analysis.market_summary(df),
        "localities": analysis.locality_metrics(df, MIN_LOCALITY_LISTINGS),
        "bhk": analysis.bhk_distribution(df),
        "furnishing": analysis.furnishing_distribution(df),
        "availability": df["locality"].value_counts().head(15).rename_axis("locality").reset_index(name="listing_count"),
        "distribution": df[df["rent"] <= df["rent"].quantile(0.98)],
        "premium": analysis.furnishing_premium(df),
        "bhk_increment": analysis.bhk_increment(df),
    }


def data_file_version() -> float:
    return analysis.CLEAN_DATA_PATH.stat().st_mtime


def title_block(title: str, subtitle: str) -> None:
    st.markdown(f'<h1 class="page-title">{title}</h1>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def market_overview(source: str, df: pd.DataFrame, data_version: float) -> None:
    data = get_market_data(source, data_version)
    kpis = data["kpis"]
    locality_df = data["localities"]
    bhk_df = data["bhk"]
    availability_df = data["availability"]
    distribution_df = data["distribution"]

    title_block(
        "Market Overview",
        "Cleaned Bengaluru rental listings with median-first analytics and sample-size protected locality rankings.",
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Total Listings", indian_number(kpis["total_listings"]), "After cleaning")
    with c2:
        kpi_card("Median Monthly Rent", inr(kpis["median_rent"]), "City-level median")
    with c3:
        kpi_card("Median Rent / sq.ft.", compact_rate(kpis["median_rent_per_sqft"]), "Calculated as rent / area")
    with c4:
        kpi_card("Localities Covered", indian_number(kpis["total_localities"]), f"Rankings use n >= {MIN_LOCALITY_LISTINGS}")

    left, right = st.columns([1.08, 0.92])
    with left:
        fig = px.histogram(
            distribution_df,
            x="rent",
            nbins=38,
            color_discrete_sequence=["#0f766e"],
            labels={"rent": "Monthly rent"},
            height=CHART_HEIGHT,
        )
        fig.update_traces(hovertemplate="Monthly rent: ₹%{x:,.0f}<br>Listings: %{y}<extra></extra>")
        fig.update_xaxes(tickprefix="₹")
        chart_container("Rental Distribution", fig)
    with right:
        fig = px.bar(
            bhk_df,
            x="beds",
            y="listing_count",
            text="listing_count",
            color="median_rent",
            color_continuous_scale=["#dcefeb", "#0f766e"],
            labels={"beds": "BHK", "listing_count": "Listings", "median_rent": "Median rent"},
            height=CHART_HEIGHT,
        )
        fig.update_traces(hovertemplate="%{x} BHK<br>Listings: %{y}<br>Median rent: ₹%{marker.color:,.0f}<extra></extra>")
        chart_container("BHK Distribution", fig)

    top_rent = locality_df.head(12).sort_values("median_rent")
    top_rate = locality_df.sort_values("median_rent_per_sqft", ascending=False).head(12).sort_values("median_rent_per_sqft")
    left, right = st.columns(2)
    with left:
        fig = px.bar(
            top_rent,
            x="median_rent",
            y="locality",
            orientation="h",
            color="listing_count",
            color_continuous_scale=["#e7eef5", "#245b7d"],
            labels={"median_rent": "Median monthly rent", "locality": "", "listing_count": "Listings"},
            height=CHART_HEIGHT,
        )
        fig.update_traces(hovertemplate="%{y}<br>Median rent: ₹%{x:,.0f}<br>Listings: %{marker.color}<extra></extra>")
        fig.update_xaxes(tickprefix="₹")
        chart_container("Locality Rent Comparison", fig)
    with right:
        fig = px.bar(
            top_rate,
            x="median_rent_per_sqft",
            y="locality",
            orientation="h",
            color="median_area",
            color_continuous_scale=["#f1e7d6", "#9a6a20"],
            labels={"median_rent_per_sqft": "Median rent / sq.ft.", "locality": "", "median_area": "Median area"},
            height=CHART_HEIGHT,
        )
        fig.update_traces(hovertemplate="%{y}<br>Median ₹/sq.ft.: %{x:.1f}<br>Median area: %{marker.color:,.0f} sq.ft.<extra></extra>")
        chart_container("Rent / sq.ft. by Locality", fig)

    fig = px.bar(
        availability_df.sort_values("listing_count"),
        x="listing_count",
        y="locality",
        orientation="h",
        color_discrete_sequence=["#34495e"],
        labels={"listing_count": "Listings", "locality": ""},
        height=CHART_HEIGHT,
    )
    fig.update_traces(hovertemplate="%{y}<br>Listings: %{x}<extra></extra>")
    chart_container("Listing Availability", fig)

    premium_df = data["premium"]
    increment_df = data["bhk_increment"]
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown('<div class="section-label">Furnishing Premium Analysis</div>', unsafe_allow_html=True)
            if premium_df.empty:
                st.info("Not enough same-locality, same-BHK furnishing groups to compare furnished and unfurnished medians reliably.")
            else:
                display = premium_df.head(8).copy()
                st.dataframe(
                    display,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "locality": "Locality",
                        "beds": "BHK",
                        "furnished_median": st.column_config.NumberColumn("Furnished median", format="₹%.0f"),
                        "semi_furnished_median": st.column_config.NumberColumn("Semi-furnished median", format="₹%.0f"),
                        "unfurnished_median": st.column_config.NumberColumn("Unfurnished median", format="₹%.0f"),
                        "furnished_vs_unfurnished_pct": st.column_config.NumberColumn("Observed difference", format="%.1f%%"),
                    },
                )
    with right:
        with st.container(border=True):
            st.markdown('<div class="section-label">BHK Increment Analysis</div>', unsafe_allow_html=True)
            if increment_df.empty:
                st.info("Not enough consecutive BHK groups within the same locality for a reliable increment view.")
            else:
                display = increment_df.head(8).copy()
                st.dataframe(
                    display,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "locality": "Locality",
                        "from_bhk": "From BHK",
                        "to_bhk": "To BHK",
                        "rent_increase_pct": st.column_config.NumberColumn("Rent increase", format="%.1f%%"),
                        "area_increase_pct": st.column_config.NumberColumn("Area increase", format="%.1f%%"),
                        "from_count": "From count",
                        "to_count": "To count",
                    },
                )

    st.caption(
        f"Correlation between area and monthly rent is {kpis['area_rent_correlation']:.2f}. "
        "This is descriptive only and should not be read as causation."
    )


def locality_explorer(source: str, df: pd.DataFrame) -> None:
    title_block("Locality Explorer", "Filter one locality and inspect BHK, furnishing, area, and rent patterns.")

    localities = sorted(df["locality"].unique())
    selected_locality = st.selectbox("Locality", localities, index=localities.index("Whitefield") if "Whitefield" in localities else 0)
    subset = df[df["locality"] == selected_locality].copy()

    if len(subset) < MIN_LOCALITY_LISTINGS:
        st.warning(f"{selected_locality} has {len(subset)} listings. Interpret charts cautiously because the sample is small.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Listings", indian_number(len(subset)))
    with c2:
        kpi_card("Median Rent", inr(subset["rent"].median()))
    with c3:
        kpi_card("Median Rent / sq.ft.", compact_rate(subset["rent_per_sqft"].median()))
    with c4:
        kpi_card("Median Property Area", f"{indian_number(subset['area'].median())} sq.ft.")

    with st.container(border=True):
        f1, f2, f3 = st.columns([1, 1, 1.2])
        with f1:
            bhk_options = sorted(subset["beds"].dropna().astype(int).unique().tolist())
            selected_bhks = st.multiselect("BHK", bhk_options, default=bhk_options)
        with f2:
            furnish_options = sorted(subset["furnishing"].unique().tolist())
            selected_furnishing = st.multiselect("Furnishing", furnish_options, default=furnish_options)
        with f3:
            rent_min, rent_max = int(subset["rent"].min()), int(subset["rent"].max())
            selected_rent = st.slider("Monthly rent range", rent_min, rent_max, (rent_min, rent_max), step=1000)

    filtered = analysis.filtered_listings(
        subset,
        beds=selected_bhks,
        furnishing=selected_furnishing,
        rent_range=(selected_rent[0], selected_rent[1]),
    )

    if filtered.empty:
        st.info("No listings match the selected filters.")
        return

    bhk_filtered = analysis.bhk_distribution(filtered)
    furnishing_filtered = analysis.furnishing_distribution(filtered)
    left, right = st.columns(2)
    with left:
        fig = px.bar(
            bhk_filtered,
            x="beds",
            y="median_rent",
            color="listing_count",
            color_continuous_scale=["#e7eef5", "#245b7d"],
            labels={"beds": "BHK", "median_rent": "Median rent", "listing_count": "Listings"},
            height=CHART_HEIGHT,
        )
        fig.update_traces(hovertemplate="%{x} BHK<br>Median rent: ₹%{y:,.0f}<br>Listings: %{marker.color}<extra></extra>")
        fig.update_yaxes(tickprefix="₹")
        chart_container("BHK-wise Rent", fig)
    with right:
        fig = px.bar(
            furnishing_filtered,
            x="furnishing",
            y="median_rent",
            color_discrete_sequence=["#0f766e"],
            labels={"furnishing": "", "median_rent": "Median rent"},
            height=CHART_HEIGHT,
        )
        fig.update_traces(hovertemplate="%{x}<br>Median rent: ₹%{y:,.0f}<extra></extra>")
        fig.update_yaxes(tickprefix="₹")
        chart_container("Furnishing Analysis", fig)

    fig = px.scatter(
        filtered,
        x="area",
        y="rent",
        color="furnishing",
        size="beds",
        hover_data={
            "locality": True,
            "beds": True,
            "furnishing": True,
            "area": ":,.0f",
            "rent": ":,.0f",
            "rent_per_sqft": ":.1f",
            "house_type": False,
        },
        labels={"area": "Area (sq.ft.)", "rent": "Monthly rent", "furnishing": "Furnishing"},
        height=430,
        color_discrete_map={"Furnished": "#245b7d", "Semi-Furnished": "#0f766e", "Unfurnished": "#9a6a20"},
    )
    fig.update_yaxes(tickprefix="₹")
    chart_container("Area vs Rent", fig)

    fig = px.histogram(
        filtered[filtered["rent"] <= filtered["rent"].quantile(0.98)],
        x="rent",
        nbins=25,
        color_discrete_sequence=["#34495e"],
        labels={"rent": "Monthly rent"},
        height=CHART_HEIGHT,
    )
    fig.update_xaxes(tickprefix="₹")
    chart_container("Rent Distribution", fig)


def compare_localities(source: str, df: pd.DataFrame) -> None:
    title_block("Compare Localities", "Select two or three localities and compare medians with sample-size context.")

    eligible = (
        df.groupby("locality")
        .size()
        .sort_values(ascending=False)
        .loc[lambda s: s >= MIN_LOCALITY_LISTINGS]
        .index.tolist()
    )
    default = [loc for loc in ["Whitefield", "Sarjapur Road", "Hebbal"] if loc in eligible][:3]
    selected = st.multiselect("Localities", eligible, default=default, max_selections=3)

    if len(selected) < 2:
        st.info("Select at least two localities to compare.")
        return

    if source == "postgres":
        import database

        metrics = database.compare_localities(selected)
        by_bhk = database.compare_localities_by_bhk(selected)
        by_furnishing = database.compare_localities_by_furnishing(selected)
    else:
        selected_df = df[df["locality"].isin(selected)]
        metrics = (
            selected_df.groupby("locality", as_index=False)
            .agg(
                listing_count=("rent", "size"),
                median_rent=("rent", "median"),
                median_rent_per_sqft=("rent_per_sqft", "median"),
                median_area=("area", "median"),
            )
        )
        by_bhk = (
            selected_df.groupby(["locality", "beds"], as_index=False)
            .agg(listing_count=("rent", "size"), median_rent=("rent", "median"))
            .query("listing_count >= 3")
        )
        by_furnishing = (
            selected_df.groupby(["locality", "furnishing"], as_index=False)
            .agg(listing_count=("rent", "size"), median_rent=("rent", "median"))
            .query("listing_count >= 3")
        )

    small = metrics[metrics["listing_count"] < MIN_LOCALITY_LISTINGS]
    if not small.empty:
        st.warning("One or more selected localities has a small listing count; comparisons should be treated as directional.")

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(
            metrics.sort_values("median_rent"),
            x="median_rent",
            y="locality",
            orientation="h",
            color="listing_count",
            color_continuous_scale=["#dcefeb", "#0f766e"],
            labels={"median_rent": "Median monthly rent", "locality": "", "listing_count": "Listings"},
            height=CHART_HEIGHT,
        )
        fig.update_xaxes(tickprefix="₹")
        chart_container("Median Monthly Rent", fig)
    with c2:
        fig = px.bar(
            metrics.sort_values("median_rent_per_sqft"),
            x="median_rent_per_sqft",
            y="locality",
            orientation="h",
            color="median_area",
            color_continuous_scale=["#f1e7d6", "#9a6a20"],
            labels={"median_rent_per_sqft": "Median rent / sq.ft.", "locality": "", "median_area": "Median area"},
            height=CHART_HEIGHT,
        )
        chart_container("Median Rent / sq.ft.", fig)

    st.dataframe(
        metrics,
        width="stretch",
        hide_index=True,
        column_config={
            "locality": "Locality",
            "listing_count": "Listings",
            "median_rent": st.column_config.NumberColumn("Median rent", format="₹%.0f"),
            "median_rent_per_sqft": st.column_config.NumberColumn("Median ₹/sq.ft.", format="₹%.1f"),
            "median_area": st.column_config.NumberColumn("Median area", format="%.0f sq.ft."),
        },
    )

    c1, c2 = st.columns(2)
    with c1:
        if by_bhk.empty:
            st.info("Not enough BHK-level listings for the selected localities.")
        else:
            fig = px.bar(
                by_bhk,
                x="beds",
                y="median_rent",
                color="locality",
                barmode="group",
                labels={"beds": "BHK", "median_rent": "Median rent", "locality": "Locality"},
                height=CHART_HEIGHT,
            )
            fig.update_yaxes(tickprefix="₹")
            chart_container("BHK-wise Comparison", fig)
    with c2:
        if by_furnishing.empty:
            st.info("Not enough furnishing-level listings for the selected localities.")
        else:
            fig = px.bar(
                by_furnishing,
                x="furnishing",
                y="median_rent",
                color="locality",
                barmode="group",
                labels={"furnishing": "", "median_rent": "Median rent", "locality": "Locality"},
                height=CHART_HEIGHT,
            )
            fig.update_yaxes(tickprefix="₹")
            chart_container("Furnishing-wise Comparison", fig)


def value_explorer(source: str, df: pd.DataFrame) -> None:
    title_block("Value Explorer", "Compare an entered rent against similar listings in the same locality and BHK.")

    localities = sorted(df["locality"].unique())
    c1, c2 = st.columns(2)
    with c1:
        locality = st.selectbox("Locality", localities, index=localities.index("Whitefield") if "Whitefield" in localities else 0)
    with c2:
        available_bhks = sorted(df[df["locality"] == locality]["beds"].dropna().astype(int).unique().tolist())
        default_bhk_index = available_bhks.index(2) if 2 in available_bhks else 0
        beds = st.selectbox("BHK", available_bhks, index=default_bhk_index)

    c1, c2 = st.columns(2)
    with c1:
        monthly_rent = st.number_input("Monthly rent", min_value=1000, max_value=1000000, value=32000, step=1000)
    with c2:
        property_area = st.number_input("Property area in sq.ft.", min_value=150, max_value=10000, value=1000, step=50)

    if monthly_rent <= 0 or property_area <= 0:
        st.warning("Enter a positive monthly rent and property area to compare against observed listings.")
        return

    if source == "postgres":
        import database

        comparable = database.value_comparables(locality, int(beds), float(property_area), MIN_COMPARABLE_LISTINGS).iloc[0].to_dict()
        comparable_count = int(comparable["comparable_count"] or 0)
        has_enough = comparable_count >= MIN_COMPARABLE_LISTINGS
    else:
        result = analysis.comparable_properties(
            df,
            locality=locality,
            beds=int(beds),
            monthly_rent=float(monthly_rent),
            property_area=float(property_area),
            min_records=MIN_COMPARABLE_LISTINGS,
        )
        has_enough = bool(result["has_enough_data"])
        comparable_count = int(result["comparable_count"])
        comparable = result

    if not has_enough:
        st.warning("Insufficient comparable listings for a reliable comparison.")
        st.caption(f"Comparable listings found: {comparable_count}. Required minimum: {MIN_COMPARABLE_LISTINGS}.")
        return

    comparable_median_rent = float(comparable["comparable_median_rent"])
    comparable_median_rate = float(comparable["comparable_median_rent_per_sqft"])
    entered_rate = monthly_rent / property_area
    rent_difference = ((monthly_rent - comparable_median_rent) / comparable_median_rent) * 100
    rate_difference = ((entered_rate - comparable_median_rate) / comparable_median_rate) * 100
    direction = "above" if rent_difference > 0 else "below" if rent_difference < 0 else "equal to"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Entered Rent", inr(monthly_rent), f"{pct(rent_difference)} vs comparable median")
    with c2:
        kpi_card("Comparable Median Rent", inr(comparable_median_rent), f"{comparable_count} comparable listings")
    with c3:
        kpi_card("Entered Rent / sq.ft.", compact_rate(entered_rate), f"{pct(rate_difference)} vs comparable rate")
    with c4:
        kpi_card("Comparable Median / sq.ft.", compact_rate(comparable_median_rate), "Same locality and BHK")

    st.markdown(
        f"""
        <div class="info-band">
            {inr(monthly_rent)}/month is {abs(rent_difference):.1f}% {direction}
            the median rent of comparable {int(beds)} BHK listings in {locality}.
        </div>
        """,
        unsafe_allow_html=True,
    )

    comparable_df = df[(df["locality"] == locality) & (df["beds"] == int(beds))].copy()
    area_matched = comparable_df[comparable_df["area"].between(property_area * 0.75, property_area * 1.25)].copy()
    if len(area_matched) >= MIN_COMPARABLE_LISTINGS:
        comparable_df = area_matched

    fig = px.scatter(
        comparable_df,
        x="area",
        y="rent",
        color="furnishing",
        labels={"area": "Area (sq.ft.)", "rent": "Monthly rent", "furnishing": "Furnishing"},
        hover_data={"area": ":,.0f", "rent": ":,.0f", "rent_per_sqft": ":.1f"},
        height=430,
    )
    fig.add_scatter(
        x=[property_area],
        y=[monthly_rent],
        mode="markers",
        marker=dict(size=16, color="#c0392b", symbol="diamond"),
        name="Entered property",
        hovertemplate=f"Entered property<br>Area: {property_area:,.0f} sq.ft.<br>Rent: ₹{monthly_rent:,.0f}<extra></extra>",
    )
    fig.update_yaxes(tickprefix="₹")
    chart_container("Comparable Listings", fig)


def main() -> None:
    inject_css()
    data_version = data_file_version()
    source, _source_error = initialize_data_source(data_version)
    df = load_all_listings(source, data_version)

    with st.sidebar:
        st.markdown("## RentScope")
        st.caption("Bengaluru Rental Market Analytics")
        st.divider()
        section = st.radio(
            "Navigate",
            ["Market Overview", "Locality Explorer", "Compare Localities", "Value Explorer"],
            label_visibility="collapsed",
        )
        st.divider()

    if section == "Market Overview":
        market_overview(source, df, data_version)
    elif section == "Locality Explorer":
        locality_explorer(source, df)
    elif section == "Compare Localities":
        compare_localities(source, df)
    else:
        value_explorer(source, df)


if __name__ == "__main__":
    main()
