# Google Ads Snapshot Anomaly Detection

Standalone demo of a snapshot-based Google Ads CSV pipeline that detects retroactive changes in reported placement impressions.

The original PR converted a pipeline from "latest file overwrites prior data" into "every CSV export becomes an immutable snapshot." A PostgreSQL view compares consecutive snapshots and a Grafana dashboard surfaces impression drops.

## What this shows

- Parses Google Ads Performance Max placement CSV exports.
- Stores each export with a `snapshot_at` timestamp.
- Preserves repeated exports for the same `report_date` instead of overwriting them.
- Uses SQL window functions to compare consecutive snapshots.
- Visualizes detected drops in Grafana.
- Includes synthetic sample CSVs that simulate impression reductions over time.

## Architecture

```text
CSV export -> parser -> PostgreSQL snapshots -> SQL change view -> Grafana dashboard
```

The key schema decision is the uniqueness constraint:

```sql
UNIQUE(platform, report_date, placement_url, source_file)
```

That allows multiple exports for the same placement and report date to coexist when they came from different source files.

## Run locally

```bash
docker compose up -d
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/load-snapshots.py \
  lambdas/google-ads/tests/snapshot_day1.csv \
  lambdas/google-ads/tests/snapshot_day5.csv \
  lambdas/google-ads/tests/snapshot_day12.csv
```

Open Grafana at `http://localhost:3001`.

Credentials:

```text
username: admin
password: admin
```

Open the `Google Ads - Anomaly Detection` dashboard and use the August-September 2025 time range.

## Repository layout

```text
db/schema.sql                              PostgreSQL table, indexes, and anomaly view
docker-compose.yml                         Local Postgres + Grafana
grafana/anomaly-detection-dashboard.json   Grafana dashboard from the implementation
lambdas/google-ads/lambda_function.py      AWS Lambda-style CSV parser and loader
lambdas/google-ads/tests/*.csv             Synthetic snapshot test data
scripts/load-snapshots.py                  Local loader for the sample snapshots
docs/architecture/anomaly-detection.md     Implementation notes
```

## Notes

This repo is intentionally public-safe: it contains only the anomaly detection implementation and synthetic data. It does not include private infrastructure docs, real cloud identifiers, real campaign data, or client-specific deployment settings.
