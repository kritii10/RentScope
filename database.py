import os
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values


CLEAN_DATA_PATH = Path("data/bengaluru_rentals_clean.csv")
MIN_LOCALITY_LISTINGS = 10


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
    DROP TABLE IF EXISTS rental_listings;

    CREATE TABLE rental_listings (
        id SERIAL PRIMARY KEY,
        house_type TEXT,
        locality TEXT NOT NULL,
        city TEXT NOT NULL,
        area NUMERIC(10, 2) NOT NULL,
        beds INTEGER NOT NULL,
        bathrooms INTEGER,
        balconies INTEGER,
        furnishing TEXT NOT NULL,
        area_rate NUMERIC(10, 2),
        rent NUMERIC(12, 2) NOT NULL,
        rent_per_sqft NUMERIC(10, 2) NOT NULL
    );

    CREATE INDEX idx_rental_listings_locality ON rental_listings (locality);
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


def load_data(path: Path = CLEAN_DATA_PATH) -> int:
    df = pd.read_csv(path)
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
        )
        for row in df.itertuples(index=False)
    ]

    sql = """
    INSERT INTO rental_listings (
        house_type, locality, city, area, beds, bathrooms, balconies,
        furnishing, area_rate, rent, rent_per_sqft
    )
    VALUES %s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)
            return len(rows)


def market_metrics() -> pd.DataFrame:
    sql = """
    SELECT
        COUNT(*)::INT AS total_listings,
        COUNT(DISTINCT locality)::INT AS total_localities,
        AVG(rent)::FLOAT AS average_rent,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent)::FLOAT AS median_rent,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent_per_sqft)::FLOAT AS median_rent_per_sqft
    FROM rental_listings
    WHERE city = 'Bengaluru';
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [column.name for column in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=columns)


def locality_metrics(min_listings: int = MIN_LOCALITY_LISTINGS) -> pd.DataFrame:
    sql = """
    SELECT
        locality,
        COUNT(*)::INT AS listing_count,
        AVG(rent)::FLOAT AS average_rent,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent)::FLOAT AS median_rent,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent_per_sqft)::FLOAT AS median_rent_per_sqft
    FROM rental_listings
    WHERE city = 'Bengaluru'
    GROUP BY locality
    HAVING COUNT(*) >= %s
    ORDER BY median_rent DESC;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (min_listings,))
            columns = [column.name for column in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=columns)
