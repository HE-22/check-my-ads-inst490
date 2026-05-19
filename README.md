# check-my-ads-inst490

This is my INST490 version of a small Check My Ads data project.

The basic issue I wanted to solve is that a Google Ads CSV export is not always stable. If you export a placement report today and then export the same report again later, some impression numbers can be lower. If the database only keeps the newest copy, there is no easy way to prove what changed.

So this project saves each CSV as its own snapshot and compares the snapshots later.

## What it does

- reads Google Ads placement CSV files
- stores each file as a separate snapshot in Postgres
- keeps the original report date from the CSV
- keeps the snapshot time, which is when that file was loaded
- compares one snapshot to the next with a SQL view
- shows the drops in a Grafana dashboard

The sample CSV files are fake data. They are only here so the project can be run without using real campaign exports.

## How the data is stored

The important part is that the table does not treat this as the same row forever:

```sql
UNIQUE(platform, report_date, placement_url, source_file)
```

That means this can happen:

```text
same placement
same report date
different CSV file
different saved row
```

Then the view `google_ads_placement_snapshot_changes` compares the rows in time order.

## Run it

Start Postgres and Grafana:

```bash
docker compose up -d
```

Set up Python:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Load the three sample snapshots:

```bash
python scripts/load-snapshots.py \
  lambdas/google-ads/tests/snapshot_day1.csv \
  lambdas/google-ads/tests/snapshot_day5.csv \
  lambdas/google-ads/tests/snapshot_day12.csv
```

Open Grafana:

```text
http://localhost:3001
```

Login:

```text
admin / admin
```

The dashboard is called `check-my-ads-inst490`. The sample data is dated around August and September 2025, so use that time range if the panels look empty.

## Files

```text
db/schema.sql
  Postgres table and the SQL view that compares snapshots

lambdas/google-ads/lambda_function.py
  CSV parsing code plus a Lambda-style S3 handler

scripts/load-snapshots.py
  Local script that loads the sample CSV files into Postgres

grafana/anomaly-detection-dashboard.json
  Dashboard for the snapshot comparison view

lambdas/google-ads/tests/
  Fake CSV exports for testing the idea locally
```

## Notes

This repo is intentionally separated from the original class/client codebase. It only includes the part I worked on for snapshot tracking and anomaly detection, with fake sample data and local Docker settings.
