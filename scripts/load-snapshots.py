"""Load the sample CSV files into the local Postgres database."""

import os
import sys
from datetime import datetime, timedelta

os.environ['PLATFORM'] = 'google-ads'
os.environ['SECRET_NAME'] = 'unused'

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambdas', 'google-ads'))

from lambda_function import parse_google_ads_csv
import psycopg2
from psycopg2.extras import execute_values


def local_db_settings():
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'campaign_data'),
        'user': os.getenv('DB_USER', 'ads_demo'),
        'password': os.getenv('DB_PASSWORD', 'ads_demo'),
    }


def save_snapshot(rows):
    conn = psycopg2.connect(**local_db_settings())
    cur = conn.cursor()
    execute_values(cur, """
        INSERT INTO google_ads_placements
        (placement_name, placement_url, placement_type, impressions,
         platform, report_date, source_file, snapshot_at, uploaded_at)
        VALUES %s
        ON CONFLICT (platform, report_date, placement_url, source_file)
        DO UPDATE SET impressions = EXCLUDED.impressions,
                      snapshot_at = EXCLUDED.snapshot_at,
                      uploaded_at = EXCLUDED.uploaded_at
    """, [
        (row['placement_name'], row['placement_url'], row['placement_type'],
         row['impressions'], row['platform'], row['report_date'],
         row['source_file'], row['snapshot_at'], row['uploaded_at'])
        for _, row in rows.iterrows()
    ])
    conn.commit()
    conn.close()


def read_csv_file(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/load-snapshots.py file1.csv file2.csv ...")
        sys.exit(1)

    # These dates are just for the class demo so the dashboard has a timeline.
    base_time = datetime(2025, 8, 26, 9, 0, 0)

    for i, path in enumerate(sys.argv[1:]):
        snapshot_at = base_time + timedelta(days=i * 5)
        file_key = f"google-ads/uploads/{os.path.basename(path)}"

        rows = parse_google_ads_csv(read_csv_file(path), file_key)
        rows['snapshot_at'] = snapshot_at
        rows['uploaded_at'] = snapshot_at
        save_snapshot(rows)

        print(f"loaded {os.path.basename(path)}: {len(rows)} rows, snapshot date {snapshot_at.date()}")

    print("\nDone. Open http://localhost:3001 to see anomalies.")


if __name__ == '__main__':
    main()
