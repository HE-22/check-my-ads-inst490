"""
Load CSV files as sequential snapshots into local PostgreSQL.

Usage:
    python scripts/load-snapshots.py snapshot_day1.csv snapshot_day5.csv snapshot_day12.csv
"""

import os
import sys
from datetime import datetime, timedelta

os.environ['PLATFORM'] = 'google-ads'
os.environ['SECRET_NAME'] = 'unused'
os.environ['S3_BUCKET_NAME'] = 'unused'

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambdas', 'google-ads'))

import psycopg2
from psycopg2.extras import execute_values
from lambda_function import parse_google_ads_csv

DB = dict(
    host=os.environ.get('DB_HOST', 'localhost'),
    port=os.environ.get('DB_PORT', '5432'),
    database=os.environ.get('DB_NAME', 'campaign_data'),
    user=os.environ.get('DB_USER', 'ads_demo'),
    password=os.environ.get('DB_PASSWORD', 'ads_demo'),
)


def insert(df):
    conn = psycopg2.connect(**DB)
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
        for _, row in df.iterrows()
    ])
    conn.commit()
    conn.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/load-snapshots.py file1.csv file2.csv ...")
        sys.exit(1)

    base_time = datetime(2025, 8, 26, 9, 0, 0)

    for i, path in enumerate(sys.argv[1:]):
        snapshot_at = base_time + timedelta(days=i * 5)
        with open(path, encoding='utf-8') as handle:
            csv_content = handle.read()

        file_key = f"google-ads/uploads/{os.path.basename(path)}"
        df = parse_google_ads_csv(csv_content, file_key)
        df['snapshot_at'] = snapshot_at
        df['uploaded_at'] = snapshot_at
        insert(df)
        print(f"Loaded {os.path.basename(path)} ({len(df)} rows, snapshot: {snapshot_at.date()})")

    print("\nDone. Open http://localhost:3001 to see anomalies.")


if __name__ == '__main__':
    main()
