from pathlib import Path

import pandas as pd


CLEAN_DATA_PATH = Path("data/bengaluru_rentals_clean.csv")
MIN_LOCALITY_LISTINGS = 10
MIN_COMPARABLE_LISTINGS = 8


def load_clean_data(path: Path = CLEAN_DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    for column in ["area", "area_rate", "rent", "rent_per_sqft"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    for column in ["beds", "bathrooms", "balconies"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")
    return df.dropna(subset=["area", "rent", "rent_per_sqft", "beds"])


def market_summary(df: pd.DataFrame) -> dict[str, float]:
    return {
        "total_listings": int(len(df)),
        "total_localities": int(df["locality"].nunique()),
        "average_rent": float(df["rent"].mean()),
        "median_rent": float(df["rent"].median()),
        "median_rent_per_sqft": float(df["rent_per_sqft"].median()),
        "average_property_area": float(df["area"].mean()),
        "median_property_area": float(df["area"].median()),
        "area_rent_correlation": float(df[["area", "rent"]].corr().iloc[0, 1]),
    }


def bhk_distribution(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("beds", as_index=False)
        .agg(
            listing_count=("rent", "size"),
            median_rent=("rent", "median"),
            median_area=("area", "median"),
            median_rent_per_sqft=("rent_per_sqft", "median"),
        )
        .sort_values("beds")
    )


def furnishing_distribution(df: pd.DataFrame) -> pd.DataFrame:
    order = ["Furnished", "Semi-Furnished", "Unfurnished"]
    result = (
        df.groupby("furnishing", as_index=False)
        .agg(listing_count=("rent", "size"), median_rent=("rent", "median"))
        .sort_values("median_rent", ascending=False)
    )
    result["furnishing"] = pd.Categorical(result["furnishing"], categories=order, ordered=True)
    return result.sort_values("furnishing").reset_index(drop=True)


def locality_metrics(df: pd.DataFrame, min_listings: int = MIN_LOCALITY_LISTINGS) -> pd.DataFrame:
    metrics = (
        df.groupby("locality", as_index=False)
        .agg(
            listing_count=("rent", "size"),
            median_rent=("rent", "median"),
            average_rent=("rent", "mean"),
            median_rent_per_sqft=("rent_per_sqft", "median"),
            median_area=("area", "median"),
        )
        .sort_values("median_rent", ascending=False)
    )
    return metrics[metrics["listing_count"] >= min_listings].reset_index(drop=True)


def filtered_listings(
    df: pd.DataFrame,
    locality: str | None = None,
    beds: list[int] | None = None,
    furnishing: list[str] | None = None,
    rent_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    filtered = df.copy()
    if locality:
        filtered = filtered[filtered["locality"] == locality]
    if beds:
        filtered = filtered[filtered["beds"].isin(beds)]
    if furnishing:
        filtered = filtered[filtered["furnishing"].isin(furnishing)]
    if rent_range:
        filtered = filtered[filtered["rent"].between(rent_range[0], rent_range[1])]
    return filtered


def comparable_properties(
    df: pd.DataFrame,
    locality: str,
    beds: int,
    monthly_rent: float,
    property_area: float,
    min_records: int = MIN_COMPARABLE_LISTINGS,
) -> dict[str, object]:
    if monthly_rent <= 0 or property_area <= 0:
        return {"has_enough_data": False, "comparable_count": 0}

    comparable = df[(df["locality"] == locality) & (df["beds"] == beds)].copy()

    lower_area = property_area * 0.75
    upper_area = property_area * 1.25
    area_matched = comparable[comparable["area"].between(lower_area, upper_area)].copy()
    if len(area_matched) >= min_records:
        comparable = area_matched

    if len(comparable) < min_records:
        return {"has_enough_data": False, "comparable_count": int(len(comparable))}

    comparable_median_rent = float(comparable["rent"].median())
    comparable_median_rate = float(comparable["rent_per_sqft"].median())
    entered_rate = monthly_rent / property_area
    rent_difference_pct = ((monthly_rent - comparable_median_rent) / comparable_median_rent) * 100
    rate_difference_pct = ((entered_rate - comparable_median_rate) / comparable_median_rate) * 100

    return {
        "has_enough_data": True,
        "comparable_count": int(len(comparable)),
        "comparable_median_rent": comparable_median_rent,
        "comparable_median_rent_per_sqft": comparable_median_rate,
        "entered_rent_per_sqft": entered_rate,
        "rent_difference_pct": rent_difference_pct,
        "rate_difference_pct": rate_difference_pct,
    }


def furnishing_premium(df: pd.DataFrame, min_records: int = 5) -> pd.DataFrame:
    grouped = (
        df.groupby(["locality", "beds", "furnishing"], as_index=False)
        .agg(listing_count=("rent", "size"), median_rent=("rent", "median"))
        .query("listing_count >= @min_records")
    )
    pivot = grouped.pivot_table(
        index=["locality", "beds"],
        columns="furnishing",
        values="median_rent",
        aggfunc="first",
    ).reset_index()
    required = {"Furnished", "Unfurnished"}
    if not required.issubset(pivot.columns):
        return pd.DataFrame()
    pivot = pivot.dropna(subset=["Furnished", "Unfurnished"]).copy()
    pivot["furnished_vs_unfurnished_pct"] = (
        (pivot["Furnished"] - pivot["Unfurnished"]) / pivot["Unfurnished"] * 100
    )
    return pivot.sort_values("furnished_vs_unfurnished_pct", ascending=False)


def bhk_increment(df: pd.DataFrame, min_records: int = 5) -> pd.DataFrame:
    grouped = (
        df.groupby(["locality", "beds"], as_index=False)
        .agg(listing_count=("rent", "size"), median_rent=("rent", "median"), median_area=("area", "median"))
        .query("listing_count >= @min_records")
        .sort_values(["locality", "beds"])
    )

    rows = []
    for locality, group in grouped.groupby("locality"):
        group = group.sort_values("beds")
        for _, current in group.iterrows():
            next_bhk = group[group["beds"] == current["beds"] + 1]
            if next_bhk.empty:
                continue
            nxt = next_bhk.iloc[0]
            rows.append(
                {
                    "locality": locality,
                    "from_bhk": int(current["beds"]),
                    "to_bhk": int(nxt["beds"]),
                    "rent_increase_pct": (nxt["median_rent"] - current["median_rent"]) / current["median_rent"] * 100,
                    "area_increase_pct": (nxt["median_area"] - current["median_area"]) / current["median_area"] * 100,
                    "from_count": int(current["listing_count"]),
                    "to_count": int(nxt["listing_count"]),
                }
            )
    return pd.DataFrame(rows).sort_values("rent_increase_pct", ascending=False) if rows else pd.DataFrame()
