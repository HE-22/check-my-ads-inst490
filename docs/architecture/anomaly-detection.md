# Snapshot-Based Anomaly Detection

## Problem

Google Ads CSV exports can change historical placement metrics when the same report is exported on different days. If a pipeline stores only the latest copy of each placement/date pair, earlier values are overwritten and the change is impossible to audit.

## Implementation

The pipeline stores every CSV export as a snapshot:

```text
same placement + same report_date + different source_file = separate historical record
```

Each parsed row receives:

- `platform`
- `report_date`
- `source_file`
- `snapshot_at`
- `uploaded_at`

The anomaly view uses `LAG()` over `(platform, placement_url, report_date)` to compare each snapshot against the previous snapshot for the same placement and reporting date.

## Detection View

`google_ads_placement_snapshot_changes` returns:

- previous and current snapshot timestamps
- previous and current source file names
- previous and current impression counts
- signed impression change
- drop amount
- drop percentage

Rows where `drop_amount > 0` represent retroactive impression decreases.

## Dashboard

The Grafana dashboard includes:

- total detected drops
- total impressions lost
- number of affected placements
- average drop percentage
- detailed placement table
- time series showing each placement's snapshot history

## Local Demonstration

The sample CSVs all represent the same report date, `August 25, 2025`, exported on simulated snapshot dates:

| File | Simulated snapshot |
|---|---|
| `snapshot_day1.csv` | 2025-08-26 |
| `snapshot_day5.csv` | 2025-08-31 |
| `snapshot_day12.csv` | 2025-09-05 |

Some placements drop to zero, some partially decrease, and some remain unchanged. That gives the dashboard realistic test coverage without including any private campaign data.
