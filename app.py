import pandas as pd
import plotly.express as px
import streamlit as st

import analysis
import database


st.set_page_config(page_title="RentScope", layout="wide")

MIN_LOCALITY_LISTINGS = analysis.MIN_LOCALITY_LISTINGS


def money(value: float) -> str:
    return f"₹{value:,.0f}"


def rate(value: float) -> str:
    return f"₹{value:,.1f}"


@st.cache_resource
def setup_database() -> None:
    database.create_table()
    database.load_data()


def show_chart(fig, caption: str) -> None:
    fig.update_layout(template="plotly_white", height=380)
    st.plotly_chart(fig, width="stretch")
    st.caption(caption)


def get_dashboard_data() -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    setup_database()
    listings = analysis.load_clean_data()
    metrics = database.market_metrics().iloc[0].to_dict()
    localities = database.locality_metrics(MIN_LOCALITY_LISTINGS)
    return listings, metrics, localities


def market_overview(df: pd.DataFrame, metrics: dict) -> None:
    st.title("Market Overview")
    st.write("Cleaned Bengaluru rental listings.")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Listings", f"{metrics['total_listings']:,.0f}")
    c2.metric("Median Rent", money(metrics["median_rent"]))
    c3.metric("Average Rent", money(metrics["average_rent"]))
    c4.metric("Median Rent / sq.ft.", rate(metrics["median_rent_per_sqft"]))
    c5.metric("Total Localities", f"{metrics['total_localities']:,.0f}")

    left, right = st.columns(2)
    with left:
        rent_data = df[df["rent"] <= df["rent"].quantile(0.98)]
        fig = px.histogram(rent_data, x="rent", nbins=35, title="Rent Distribution")
        fig.update_xaxes(title="Monthly rent", tickprefix="₹")
        fig.update_yaxes(title="Listings")
        show_chart(fig, "Shows how monthly rents are spread across Bengaluru listings.")
    with right:
        bhk = analysis.bhk_distribution(df)
        fig = px.bar(bhk, x="beds", y="average_rent", title="Average Rent by BHK")
        fig.update_xaxes(title="BHK")
        fig.update_yaxes(title="Average rent", tickprefix="₹")
        show_chart(fig, "Shows how the average monthly rent changes for each BHK type.")


def locality_explorer(df: pd.DataFrame) -> None:
    st.title("Locality Explorer")

    localities = sorted(df["locality"].dropna().unique())
    default_index = localities.index("Whitefield") if "Whitefield" in localities else 0
    locality = st.selectbox("Locality", localities, index=default_index)

    subset = df[df["locality"] == locality].copy()
    bhk_options = sorted(subset["beds"].astype(int).unique())
    furnishing_options = sorted(subset["furnishing"].unique())

    left, right = st.columns(2)
    selected_bhk = left.multiselect("BHK", bhk_options, default=bhk_options)
    selected_furnishing = right.multiselect(
        "Furnishing type",
        furnishing_options,
        default=furnishing_options,
    )

    filtered = subset[
        subset["beds"].astype(int).isin(selected_bhk)
        & subset["furnishing"].isin(selected_furnishing)
    ]

    if filtered.empty:
        st.warning("No listings match these filters.")
        return

    left, right = st.columns(2)
    with left:
        furnishing = analysis.furnishing_distribution(filtered)
        fig = px.bar(furnishing, x="furnishing", y="median_rent", title="Median Rent by Furnishing")
        fig.update_xaxes(title="Furnishing")
        fig.update_yaxes(title="Median rent", tickprefix="₹")
        show_chart(fig, "Shows how the median rent changes by furnishing type in the selected locality.")
    with right:
        bhk = analysis.bhk_distribution(filtered)
        fig = px.line(bhk, x="beds", y="median_rent", markers=True, title="BHK versus Median Rent")
        fig.update_xaxes(title="BHK")
        fig.update_yaxes(title="Median rent", tickprefix="₹")
        show_chart(fig, "Shows how the typical rent changes as the BHK count increases.")


def compare_localities(localities: pd.DataFrame) -> None:
    st.title("Compare Localities")

    options = localities["locality"].tolist()
    default = [loc for loc in ["Whitefield", "Sarjapur Road", "Hebbal"] if loc in options]
    selected = st.multiselect("Choose localities", options, default=default[:3], max_selections=3)

    if len(selected) < 2:
        st.warning("Select at least two localities.")
        return

    selected_metrics = localities[localities["locality"].isin(selected)]

    left, right = st.columns(2)
    with left:
        fig = px.bar(selected_metrics, x="locality", y="median_rent", title="Median Rent Comparison")
        fig.update_traces(marker_color="#0f766e")
        fig.update_xaxes(title="Locality")
        fig.update_yaxes(title="Median rent", tickprefix="₹")
        show_chart(fig, "Compares the typical monthly rent across the selected localities.")
    with right:
        fig = px.bar(selected_metrics, x="locality", y="average_rent", title="Average Rent Comparison")
        fig.update_traces(marker_color="#2563eb")
        fig.update_xaxes(title="Locality")
        fig.update_yaxes(title="Average rent", tickprefix="₹")
        show_chart(fig, "Compares the average monthly rent across the selected localities.")

    _, middle, _ = st.columns([1, 2, 1])
    with middle:
        fig = px.bar(
            selected_metrics,
            x="locality",
            y="median_rent_per_sqft",
            title="Rent per sq.ft. Comparison",
        )
        fig.update_traces(marker_color="#7c3aed")
        fig.update_xaxes(title="Locality")
        fig.update_yaxes(title="Median rent per sq.ft.")
        show_chart(fig, "Compares rent after adjusting for property size.")


def main() -> None:
    st.sidebar.title("RentScope")
    page = st.sidebar.radio(
        "Pages",
        ["Market Overview", "Locality Explorer", "Compare Localities"],
    )

    try:
        df, metrics, localities = get_dashboard_data()
    except Exception as error:
        st.error("PostgreSQL is not connected. Create the database and update your .env file.")
        st.code(str(error))
        return

    if page == "Market Overview":
        market_overview(df, metrics)
    elif page == "Locality Explorer":
        locality_explorer(df)
    else:
        compare_localities(localities)


if __name__ == "__main__":
    main()
