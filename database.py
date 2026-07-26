import hashlib
import os
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values


CLEAN_DATA_PATH = Path("data/bengaluru_rentals_clean.csv")
MIN_LOCALITY_LISTINGS = 10
MIN_COMPARABLE_LISTINGS = 8


def get_connection():
    load_dotenv()
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "rentscope"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


def create_table() -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS rental_listings (
        id SERIAL PRIMARY KEY,
        house_type TEXT NOT NULL,
        locality TEXT NOT NULL,
        city TEXT NOT NULL,
        area NUMERIC(10, 2) NOT NULL CHECK (area > 0),
        beds INTEGER NOT NULL CHECK (beds > 0),
        bathrooms INTEGER NOT NULL CHECK (bathrooms >= 0),
        balconies INTEGER NOT NULL CHECK (balconies >= 0),
        furnishing TEXT NOT NULL,
        area_rate NUMERIC(10, 2),
        rent NUMERIC(12, 2) NOT NULL CHECK (rent > 0),
        rent_per_sqft NUMERIC(10, 2) NOT NULL CHECK (rent_per_sqft > 0),
        source_hash TEXT NOT NULL UNIQUE,
        loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_rental_listings_locality ON rental_listings (locality);
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


def row_hash(row: pd.Series) -> str:
    parts = [
        row["house_type"],
        row["locality"],
        row["city"],
        f"{row['area']:.2f}",
        str(int(row["beds"])),
        str(int(row["bathrooms"])),
        str(int(row["balconies"])),
        row["furnishing"],
        f"{row['rent']:.2f}",
        f"{row['rent_per_sqft']:.2f}",
    ]
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()


def load_clean_data_to_postgres(path: Path = CLEAN_DATA_PATH) -> int:
    df = pd.read_csv(path)
    df["source_hash"] = df.apply(row_hash, axis=1)
    rows = [
        (
            row.house_type,
            row.locality,
            row.city,
            row.area,
            int(row.beds),
            int(row.bathrooms),
            int(row.balconies),
            row.furnishing,
            row.area_rate,
            row.rent,
            row.rent_per_sqft,
            row.source_hash,
        )
        for row in df.itertuples(index=False)
    ]
    if not rows:
        return 0

    insert_sql = """
    INSERT INTO rental_listings (
        house_type, locality, city, area, beds, bathrooms, balconies,
        furnishing, area_rate, rent, rent_per_sqft, source_hash
    )
    VALUES %s
    ON CONFLICT (source_hash) DO NOTHING;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM rental_listings WHERE NOT (source_hash = ANY(%s));",
                (df["source_hash"].tolist(),),
            )
            execute_values(cur, insert_sql, rows)
            return cur.rowcount


def ensure_database_ready() -> None:
    create_table()
    load_clean_data_to_postgres()


def query_df(sql: str, params: tuple | dict | None = None) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def market_kpis() -> pd.DataFrame:
    return query_df(
        """
        SELECT
            COUNT(*)::INT AS total_listings,
            COUNT(DISTINCT locality)::INT AS total_localities,
            AVG(rent)::FLOAT AS average_rent,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent)::FLOAT AS median_rent,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent_per_sqft)::FLOAT AS median_rent_per_sqft,
            AVG(area)::FLOAT AS average_property_area,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY area)::FLOAT AS median_property_area,
            CORR(area, rent)::FLOAT AS area_rent_correlation
        FROM rental_listings
        WHERE city = 'Bengaluru';
        """
    )


def locality_metrics(min_listings: int = MIN_LOCALITY_LISTINGS) -> pd.DataFrame:
    return query_df(
        """
        SELECT
            locality,
            COUNT(*)::INT AS listing_count,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent)::FLOAT AS median_rent,
            AVG(rent)::FLOAT AS average_rent,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent_per_sqft)::FLOAT AS median_rent_per_sqft,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY area)::FLOAT AS median_area,
            MIN(rent)::FLOAT AS min_rent,
            MAX(rent)::FLOAT AS max_rent
        FROM rental_listings
        WHERE city = 'Bengaluru'
        GROUP BY locality
        HAVING COUNT(*) >= %s
        ORDER BY median_rent DESC;
        """,
        (min_listings,),
    )


def bhk_metrics() -> pd.DataFrame:
    return query_df(
        """
        SELECT
            beds,
            COUNT(*)::INT AS listing_count,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent)::FLOAT AS median_rent,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY area)::FLOAT AS median_area,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent_per_sqft)::FLOAT AS median_rent_per_sqft,
            MIN(rent)::FLOAT AS min_rent,
            MAX(rent)::FLOAT AS max_rent
        FROM rental_listings
        WHERE city = 'Bengaluru'
        GROUP BY beds
        ORDER BY beds;
        """
    )


def furnishing_metrics() -> pd.DataFrame:
    return query_df(
        """
        SELECT
            furnishing,
            COUNT(*)::INT AS listing_count,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent)::FLOAT AS median_rent,
            AVG(rent)::FLOAT AS average_rent,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent_per_sqft)::FLOAT AS median_rent_per_sqft
        FROM rental_listings
        WHERE city = 'Bengaluru'
        GROUP BY furnishing
        ORDER BY median_rent DESC;
        """
    )


def listing_availability(limit: int = 15) -> pd.DataFrame:
    return query_df(
        """
        SELECT locality, COUNT(*)::INT AS listing_count
        FROM rental_listings
        WHERE city = 'Bengaluru'
        GROUP BY locality
        ORDER BY listing_count DESC, locality
        LIMIT %s;
        """,
        (limit,),
    )


def rental_distribution() -> pd.DataFrame:
    return query_df(
        """
        WITH bounds AS (
            SELECT PERCENTILE_CONT(0.98) WITHIN GROUP (ORDER BY rent) AS p98_rent
            FROM rental_listings
            WHERE city = 'Bengaluru'
        )
        SELECT r.*
        FROM rental_listings r
        CROSS JOIN bounds b
        WHERE r.city = 'Bengaluru' AND r.rent <= b.p98_rent
        ORDER BY r.rent;
        """
    )


def listings(
    locality: str | None = None,
    beds: list[int] | None = None,
    furnishing: list[str] | None = None,
    rent_min: float | None = None,
    rent_max: float | None = None,
) -> pd.DataFrame:
    clauses = ["city = 'Bengaluru'"]
    params: list[object] = []
    if locality:
        clauses.append("locality = %s")
        params.append(locality)
    if beds:
        clauses.append("beds = ANY(%s)")
        params.append(beds)
    if furnishing:
        clauses.append("furnishing = ANY(%s)")
        params.append(furnishing)
    if rent_min is not None:
        clauses.append("rent >= %s")
        params.append(rent_min)
    if rent_max is not None:
        clauses.append("rent <= %s")
        params.append(rent_max)

    where_sql = " AND ".join(clauses)
    return query_df(
        f"""
        SELECT
            id, house_type, locality, city, area, beds, bathrooms, balconies,
            furnishing, area_rate, rent, rent_per_sqft
        FROM rental_listings
        WHERE {where_sql}
        ORDER BY locality, beds, rent;
        """,
        tuple(params),
    )


def locality_bhk_metrics(locality: str) -> pd.DataFrame:
    return query_df(
        """
        SELECT
            beds,
            COUNT(*)::INT AS listing_count,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent)::FLOAT AS median_rent,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY area)::FLOAT AS median_area,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent_per_sqft)::FLOAT AS median_rent_per_sqft
        FROM rental_listings
        WHERE city = 'Bengaluru' AND locality = %s
        GROUP BY beds
        ORDER BY beds;
        """,
        (locality,),
    )


def locality_furnishing_metrics(locality: str, beds: list[int] | None = None) -> pd.DataFrame:
    params: list[object] = [locality]
    beds_filter = ""
    if beds:
        beds_filter = "AND beds = ANY(%s)"
        params.append(beds)
    return query_df(
        f"""
        SELECT
            furnishing,
            COUNT(*)::INT AS listing_count,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent)::FLOAT AS median_rent
        FROM rental_listings
        WHERE city = 'Bengaluru' AND locality = %s {beds_filter}
        GROUP BY furnishing
        ORDER BY median_rent DESC;
        """,
        tuple(params),
    )


def compare_localities(localities: list[str]) -> pd.DataFrame:
    return query_df(
        """
        SELECT
            locality,
            COUNT(*)::INT AS listing_count,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent)::FLOAT AS median_rent,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent_per_sqft)::FLOAT AS median_rent_per_sqft,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY area)::FLOAT AS median_area
        FROM rental_listings
        WHERE city = 'Bengaluru' AND locality = ANY(%s)
        GROUP BY locality
        ORDER BY locality;
        """,
        (localities,),
    )


def compare_localities_by_bhk(localities: list[str]) -> pd.DataFrame:
    return query_df(
        """
        SELECT
            locality,
            beds,
            COUNT(*)::INT AS listing_count,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent)::FLOAT AS median_rent
        FROM rental_listings
        WHERE city = 'Bengaluru' AND locality = ANY(%s)
        GROUP BY locality, beds
        HAVING COUNT(*) >= 3
        ORDER BY beds, locality;
        """,
        (localities,),
    )


def compare_localities_by_furnishing(localities: list[str]) -> pd.DataFrame:
    return query_df(
        """
        SELECT
            locality,
            furnishing,
            COUNT(*)::INT AS listing_count,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent)::FLOAT AS median_rent
        FROM rental_listings
        WHERE city = 'Bengaluru' AND locality = ANY(%s)
        GROUP BY locality, furnishing
        HAVING COUNT(*) >= 3
        ORDER BY furnishing, locality;
        """,
        (localities,),
    )


def value_comparables(locality: str, beds: int, area: float, min_records: int = MIN_COMPARABLE_LISTINGS) -> pd.DataFrame:
    return query_df(
        """
        WITH base AS (
            SELECT *
            FROM rental_listings
            WHERE city = 'Bengaluru' AND locality = %s AND beds = %s
        ),
        area_matched AS (
            SELECT *
            FROM base
            WHERE area BETWEEN %s AND %s
        ),
        chosen AS (
            SELECT * FROM area_matched
            WHERE (SELECT COUNT(*) FROM area_matched) >= %s
            UNION ALL
            SELECT * FROM base
            WHERE (SELECT COUNT(*) FROM area_matched) < %s
        )
        SELECT
            COUNT(*)::INT AS comparable_count,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent)::FLOAT AS comparable_median_rent,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent_per_sqft)::FLOAT AS comparable_median_rent_per_sqft,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY area)::FLOAT AS comparable_median_area
        FROM chosen;
        """,
        (locality, beds, area * 0.75, area * 1.25, min_records, min_records),
    )


def furnishing_premium(min_records: int = 5) -> pd.DataFrame:
    return query_df(
        """
        WITH grouped AS (
            SELECT
                locality,
                beds,
                furnishing,
                COUNT(*)::INT AS listing_count,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent)::FLOAT AS median_rent
            FROM rental_listings
            WHERE city = 'Bengaluru'
            GROUP BY locality, beds, furnishing
            HAVING COUNT(*) >= %s
        ),
        pivoted AS (
            SELECT
                locality,
                beds,
                MAX(CASE WHEN furnishing = 'Furnished' THEN median_rent END) AS furnished_median,
                MAX(CASE WHEN furnishing = 'Semi-Furnished' THEN median_rent END) AS semi_furnished_median,
                MAX(CASE WHEN furnishing = 'Unfurnished' THEN median_rent END) AS unfurnished_median
            FROM grouped
            GROUP BY locality, beds
        )
        SELECT
            locality,
            beds,
            furnished_median,
            semi_furnished_median,
            unfurnished_median,
            ((furnished_median - unfurnished_median) / unfurnished_median * 100)::FLOAT
                AS furnished_vs_unfurnished_pct
        FROM pivoted
        WHERE furnished_median IS NOT NULL AND unfurnished_median IS NOT NULL
        ORDER BY furnished_vs_unfurnished_pct DESC;
        """,
        (min_records,),
    )


def bhk_increment(min_records: int = 5) -> pd.DataFrame:
    return query_df(
        """
        WITH bhk_metrics AS (
            SELECT
                locality,
                beds,
                COUNT(*)::INT AS listing_count,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent)::FLOAT AS median_rent,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY area)::FLOAT AS median_area
            FROM rental_listings
            WHERE city = 'Bengaluru'
            GROUP BY locality, beds
            HAVING COUNT(*) >= %s
        )
        SELECT
            current.locality,
            current.beds AS from_bhk,
            next_bhk.beds AS to_bhk,
            ((next_bhk.median_rent - current.median_rent) / current.median_rent * 100)::FLOAT
                AS rent_increase_pct,
            ((next_bhk.median_area - current.median_area) / current.median_area * 100)::FLOAT
                AS area_increase_pct,
            current.listing_count AS from_count,
            next_bhk.listing_count AS to_count
        FROM bhk_metrics current
        JOIN bhk_metrics next_bhk
            ON current.locality = next_bhk.locality
            AND next_bhk.beds = current.beds + 1
        ORDER BY rent_increase_pct DESC;
        """,
        (min_records,),
    )
