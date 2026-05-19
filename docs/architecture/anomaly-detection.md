# Anomaly Detection Notes

This file is just a short write-up of the idea behind the project.

## What we were trying to catch

If a Google Ads placement report gets exported more than once, the old numbers can change. The problem is that a normal database import usually updates the existing row, so the older number disappears.

For this project we wanted the database to keep the history instead.

## The approach

Each CSV load gets a `snapshot_at` timestamp. The source file name is also saved. A placement can appear multiple times for the same report date as long as it came from a different CSV file.

The view uses `LAG()` to look at the previous snapshot for the same placement URL and report date.

If the new impression count is lower than the previous one, the view calculates:

- how many impressions dropped
- the percent drop
- which source file had the old number
- which source file had the new number

## Local test data

The three CSV files all use the same report date:

```text
August 25, 2025
```

The loader pretends they were saved on different days. Some rows go down, some stay the same, and some go all the way to zero. That is enough to test the SQL and the dashboard without putting real data in this public repo.
