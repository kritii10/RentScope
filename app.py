import pandas as pd
import plotly.express as px
import streamlit as st

import analysis
import database


st.set_page_config(page_title="RentScope", layout="wide")

MIN_LOCALITY_LISTINGS = analysis.MIN_LOCALITY_LISTINGS
MIN_COMPARABLE_LISTINGS = analysis.MIN_COMPARABLE_LISTINGS


def money(value: float) -> str:
    return f"₹{value:,.0f}"


def rate(value: float) -> str:
    return f"₹{value:,.1f}"


@st.cache_resource
def setup_database() -> None:
    database.create_table()
    database.load_clean_data_to_postgres()


def chart(fig):
    fig.update_layout(template="plotly_white", height=380)
    st.plotly_chart(fig, width="stretch")


def load_data() -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    setup_database()
    listings = database.listings()
    kpis = database.market_kpis().iloc[0].to_dict()
    localities = database.locality_metrics(MIN_LOCALITY_LISTINGS)
    return listings, kpis, localities


def market_overview(df: pd.DataFrame, kpis: dict, localities: pd.DataFrame) -> None:
    st.title("Market Overview")
    st.write("Bengaluru rental listings after cleaning.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Listings", f"{kpis['total_listings']:,.0f}")
    c2.metric("Median Rent", money(kpis["median_rent"]))
    c3.metric("Median Rent / sq.ft.", rate(kpis["median_rent_per_sqft"]))
    c4.metric("Localities", f"{kpis['total_localities']:,.0f}")

    left, right = st.columns(2)
    with left:
        rent_data = df[df["rent"] <= df["rent"].quantile(0.98)]
        fig = px.histogram(rent_data, x="rent", nbins=35, title="Rent Distribution")
        fig.update_xaxes(tickprefix="₹", title="Monthly rent")
        chart(fig)
    with right:
        bhk = analysis.bhk_distribution(df)
        fig = px.bar(bhk, x="beds", y="listing_count", title="BHK Distribution", text="listing_count")
        fig.update_xaxes(title="BHK")
        fig.update_yaxes(title="Listings")
        chart(fig)

    left, right = st.columns(2)
    with left:
        top_rent = localities.head(10).sort_values("median_rent")
        fig = px.bar(
            top_rent,
            x="median_rent",
            y="locality",
            orientation="h",
            title="Top Localities by Median Rent",
        )
        fig.update_xaxes(tickprefix="₹")
        chart(fig)
    with right:
        top_rate = localities.sort_values("median_rent_per_sqft", ascending=False).head(10)
        top_rate = top_rate.sort_values("median_rent_per_sqft")
        fig = px.bar(
            top_rate,
            x="median_rent_per_sqft",
            y="locality",
            orientation="h",
            title="Top Localities by Rent / sq.ft.",
        )
        chart(fig)

    st.subheader("Furnishing Analysis")
    furnishing = analysis.furnishing_distribution(df)
    fig = px.bar(furnishing, x="furnishing", y="median_rent", title="Median Rent by Furnishing")
    fig.update_yaxes(tickprefix="₹")
    chart(fig)


def locality_explorer(df: pd.DataFrame) -> None:
    st.title("Locality Explorer")

    locality = st.selectbox("Choose locality", sorted(df["locality"].unique()))
    subset = df[df["locality"] == locality].copy()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Listings", f"{len(subset):,.0f}")
    c2.metric("Median Rent", money(subset["rent"].median()))
    c3.metric("Median Rent / sq.ft.", rate(subset["rent_per_sqft"].median()))
    c4.metric("Median Area", f"{subset['area'].median():,.0f} sq.ft.")

    bhk_options = sorted(subset["beds"].astype(int).unique())
    furnishing_options = sorted(subset["furnishing"].unique())

    c1, c2, c3 = st.columns(3)
    selected_bhk = c1.multiselect("BHK", bhk_options, default=bhk_options)
    selected_furnishing = c2.multiselect("Furnishing", furnishing_options, default=furnishing_options)
    rent_min, rent_max = int(subset["rent"].min()), int(subset["rent"].max())
    selected_rent = c3.slider("Rent range", rent_min, rent_max, (rent_min, rent_max), step=1000)

    filtered = subset[
        subset["beds"].isin(selected_bhk)
        & subset["furnishing"].isin(selected_furnishing)
        & subset["rent"].between(selected_rent[0], selected_rent[1])
    ]

    if filtered.empty:
        st.warning("No listings match these filters.")
        return

    left, right = st.columns(2)
    with left:
        bhk = analysis.bhk_distribution(filtered)
        fig = px.bar(bhk, x="beds", y="median_rent", title="Median Rent by BHK")
        fig.update_yaxes(tickprefix="₹")
        chart(fig)
    with right:
        furnishing = analysis.furnishing_distribution(filtered)
        fig = px.bar(furnishing, x="furnishing", y="median_rent", title="Median Rent by Furnishing")
        fig.update_yaxes(tickprefix="₹")
        chart(fig)

    fig = px.scatter(
        filtered,
        x="area",
        y="rent",
        color="furnishing",
        hover_data=["locality", "beds", "rent_per_sqft"],
        title="Area vs Rent",
    )
    fig.update_yaxes(tickprefix="₹")
    chart(fig)


def compare_localities(df: pd.DataFrame, localities: pd.DataFrame) -> None:
    st.title("Compare Localities")

    options = localities["locality"].tolist()
    default = [loc for loc in ["Whitefield", "Sarjapur Road", "Hebbal"] if loc in options]
    selected = st.multiselect("Choose 2 or 3 localities", options, default=default[:3], max_selections=3)

    if len(selected) < 2:
        st.warning("Select at least two localities.")
        return

    selected_metrics = localities[localities["locality"].isin(selected)]
    selected_rows = df[df["locality"].isin(selected)]

    st.dataframe(selected_metrics, width="stretch", hide_index=True)

    left, right = st.columns(2)
    with left:
        fig = px.bar(selected_metrics, x="locality", y="median_rent", title="Median Rent")
        fig.update_yaxes(tickprefix="₹")
        chart(fig)
    with right:
        fig = px.bar(selected_metrics, x="locality", y="median_rent_per_sqft", title="Median Rent / sq.ft.")
        chart(fig)

    bhk = (
        selected_rows.groupby(["locality", "beds"], as_index=False)
        .agg(median_rent=("rent", "median"), listing_count=("rent", "size"))
        .query("listing_count >= 3")
    )
    fig = px.bar(bhk, x="beds", y="median_rent", color="locality", barmode="group", title="BHK-wise Comparison")
    fig.update_yaxes(tickprefix="₹")
    chart(fig)


def value_explorer(df: pd.DataFrame) -> None:
    st.title("Value Explorer")

    locality = st.selectbox("Locality", sorted(df["locality"].unique()))
    bhk_options = sorted(df[df["locality"] == locality]["beds"].astype(int).unique())
    beds = st.selectbox("BHK", bhk_options)

    c1, c2 = st.columns(2)
    monthly_rent = c1.number_input("Monthly rent", min_value=1000, value=32000, step=1000)
    property_area = c2.number_input("Area in sq.ft.", min_value=150, value=1000, step=50)

    result = analysis.comparable_properties(
        df,
        locality=locality,
        beds=int(beds),
        monthly_rent=float(monthly_rent),
        property_area=float(property_area),
        min_records=MIN_COMPARABLE_LISTINGS,
    )

    if not result["has_enough_data"]:
        st.warning("Insufficient comparable listings for this locality and BHK.")
        st.write(f"Comparable listings found: {result['comparable_count']}")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entered Rent", money(monthly_rent))
    c2.metric("Comparable Median Rent", money(result["comparable_median_rent"]))
    c3.metric("Entered Rent / sq.ft.", rate(result["entered_rent_per_sqft"]))
    c4.metric("Comparable Rent / sq.ft.", rate(result["comparable_median_rent_per_sqft"]))

    st.write(f"Difference from comparable median rent: {result['rent_difference_pct']:.1f}%")

    comparable = df[(df["locality"] == locality) & (df["beds"] == int(beds))]
    fig = px.scatter(comparable, x="area", y="rent", color="furnishing", title="Comparable Listings")
    fig.add_scatter(x=[property_area], y=[monthly_rent], mode="markers", name="Entered property")
    fig.update_yaxes(tickprefix="₹")
    chart(fig)


def main() -> None:
    st.sidebar.title("RentScope")
    page = st.sidebar.radio(
        "Pages",
        ["Market Overview", "Locality Explorer", "Compare Localities", "Value Explorer"],
    )

    try:
        df, kpis, localities = load_data()
    except Exception as error:
        st.error("PostgreSQL is not connected. Create the database and update your .env file.")
        st.code(str(error))
        return

    if page == "Market Overview":
        market_overview(df, kpis, localities)
    elif page == "Locality Explorer":
        locality_explorer(df)
    elif page == "Compare Localities":
        compare_localities(df, localities)
    else:
        value_explorer(df)


if __name__ == "__main__":
    main()
