from pathlib import Path

import pandas as pd


RAW_DATA_PATH = Path("data/cities_magicbricks_rental_prices.csv")
CLEAN_DATA_PATH = Path("data/bengaluru_rentals_clean.csv")

CRITICAL_COLUMNS = [
    "house_type",
    "locality",
    "city",
    "area",
    "beds",
    "bathrooms",
    "balconies",
    "furnishing",
    "rent",
]


def clean_text(value: object) -> str:
    return " ".join(str(value).strip().split())


def normalize_locality(value: object) -> str:
    text = clean_text(value)
    text = text.replace(" ,", ",").replace(", ", ", ")
    return text.title().replace("Hsr", "HSR").replace("Jp ", "JP ").replace("Kr ", "KR ")


def normalize_furnishing(value: object) -> str:
    normalized = clean_text(value).lower().replace("_", "-").replace(" ", "-")
    mapping = {
        "furnished": "Furnished",
        "semi-furnished": "Semi-Furnished",
        "semifurnished": "Semi-Furnished",
        "semi": "Semi-Furnished",
        "unfurnished": "Unfurnished",
        "un-furnished": "Unfurnished",
    }
    return mapping.get(normalized, clean_text(value).title())


def iqr_bounds(series: pd.Series, multiplier: float = 3.0) -> tuple[float, float]:
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    return q1 - multiplier * iqr, q3 + multiplier * iqr


def clean_bengaluru_rentals(raw_path: Path = RAW_DATA_PATH) -> tuple[pd.DataFrame, dict[str, int]]:
    df = pd.read_csv(raw_path)
    original_rows = len(df)

    df.columns = [column.strip().lower() for column in df.columns]
    df["city_clean"] = df["city"].astype(str).str.strip().str.lower()
    bengaluru = df[df["city_clean"].isin(["bangalore", "bengaluru"])].copy()
    bengaluru_rows = len(bengaluru)

    before_duplicates = len(bengaluru)
    bengaluru = bengaluru.drop_duplicates()
    duplicates_removed = before_duplicates - len(bengaluru)

    for column in ["area", "beds", "bathrooms", "balconies", "area_rate", "rent"]:
        bengaluru[column] = pd.to_numeric(bengaluru[column], errors="coerce")

    bengaluru["house_type"] = bengaluru["house_type"].map(clean_text)
    bengaluru["locality"] = bengaluru["locality"].map(normalize_locality)
    bengaluru["city"] = "Bengaluru"
    bengaluru["furnishing"] = bengaluru["furnishing"].map(normalize_furnishing)

    before_invalid = len(bengaluru)
    bengaluru = bengaluru.dropna(subset=CRITICAL_COLUMNS)
    bengaluru = bengaluru[
        (bengaluru["area"] >= 150)
        & (bengaluru["area"] <= 10000)
        & (bengaluru["rent"] >= 3000)
        & (bengaluru["rent"] <= 1000000)
        & (bengaluru["beds"].between(1, 8))
        & (bengaluru["bathrooms"].between(1, 10))
        & (bengaluru["balconies"].between(0, 10))
        & (bengaluru["furnishing"].isin(["Furnished", "Semi-Furnished", "Unfurnished"]))
    ].copy()
    invalid_removed = before_invalid - len(bengaluru)

    bengaluru["rent_per_sqft"] = bengaluru["rent"] / bengaluru["area"]

    # Rent and area are allowed to be high for premium homes. A reproducible
    # rent-per-square-foot outlier check is a better signal for suspicious rows.
    rate_low, rate_high = iqr_bounds(bengaluru["rent_per_sqft"], multiplier=3.0)

    before_outliers = len(bengaluru)
    bengaluru = bengaluru[
        bengaluru["rent_per_sqft"].between(max(3, rate_low), min(500, rate_high))
    ].copy()
    outliers_removed = before_outliers - len(bengaluru)

    integer_columns = ["beds", "bathrooms", "balconies"]
    for column in integer_columns:
        bengaluru[column] = bengaluru[column].astype(int)

    numeric_columns = ["area", "area_rate", "rent", "rent_per_sqft"]
    for column in numeric_columns:
        bengaluru[column] = bengaluru[column].round(2)

    columns = [
        "house_type",
        "locality",
        "city",
        "area",
        "beds",
        "bathrooms",
        "balconies",
        "furnishing",
        "area_rate",
        "rent",
        "rent_per_sqft",
    ]
    bengaluru = bengaluru[columns].sort_values(["locality", "beds", "rent"]).reset_index(drop=True)

    summary = {
        "original_rows": original_rows,
        "bengaluru_rows": bengaluru_rows,
        "duplicates_removed": duplicates_removed,
        "invalid_records_removed": invalid_removed,
        "outliers_removed": outliers_removed,
        "final_rows": len(bengaluru),
    }

    return bengaluru, summary


def main() -> None:
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(f"Raw dataset not found: {RAW_DATA_PATH}")

    CLEAN_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    clean_df, summary = clean_bengaluru_rentals(RAW_DATA_PATH)
    clean_df.to_csv(CLEAN_DATA_PATH, index=False)

    print("\nCleaning summary")
    print("----------------")
    for key, value in summary.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    print(f"\nSaved cleaned data to {CLEAN_DATA_PATH}")


if __name__ == "__main__":
    main()
