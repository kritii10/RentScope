from pathlib import Path

import pandas as pd


CLEAN_DATA_PATH = Path("data/bengaluru_rentals_clean.csv")
MIN_LOCALITY_LISTINGS = 10


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
    }


def bhk_distribution(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("beds", as_index=False)
        .agg(
            listing_count=("rent", "size"),
            median_rent=("rent", "median"),
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
            median_rent_per_sqft=("rent_per_sqft", "median"),
        )
        .sort_values("median_rent", ascending=False)
    )
    return metrics[metrics["listing_count"] >= min_listings].reset_index(drop=True)
