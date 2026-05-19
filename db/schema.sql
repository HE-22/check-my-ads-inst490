-- Google Ads snapshot anomaly detection demo schema.

CREATE TABLE IF NOT EXISTS google_ads_placements (
    id SERIAL PRIMARY KEY,
    placement_name TEXT NOT NULL,
    placement_url TEXT NOT NULL,
    placement_type TEXT,
    impressions INTEGER DEFAULT 0,
    platform VARCHAR(50) NOT NULL DEFAULT 'google-ads',
    report_date DATE NOT NULL,
    source_file TEXT NOT NULL,
    snapshot_at TIMESTAMP NOT NULL,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(platform, report_date, placement_url, source_file)
);

CREATE INDEX IF NOT EXISTS idx_placements_date ON google_ads_placements(report_date);
CREATE INDEX IF NOT EXISTS idx_placements_type ON google_ads_placements(placement_type);
CREATE INDEX IF NOT EXISTS idx_placements_impressions ON google_ads_placements(impressions) WHERE impressions > 0;
CREATE INDEX IF NOT EXISTS idx_placements_snapshot_at ON google_ads_placements(snapshot_at);
CREATE INDEX IF NOT EXISTS idx_placements_snapshot_lookup
    ON google_ads_placements(platform, placement_url, report_date, snapshot_at);

CREATE OR REPLACE VIEW google_ads_placement_snapshot_changes AS
WITH ordered_snapshots AS (
    SELECT
        platform,
        placement_name,
        placement_url,
        placement_type,
        report_date,
        source_file,
        snapshot_at,
        impressions,
        LAG(snapshot_at) OVER (
            PARTITION BY platform, placement_url, report_date
            ORDER BY snapshot_at, source_file
        ) AS previous_snapshot_at,
        LAG(source_file) OVER (
            PARTITION BY platform, placement_url, report_date
            ORDER BY snapshot_at, source_file
        ) AS previous_source_file,
        LAG(impressions) OVER (
            PARTITION BY platform, placement_url, report_date
            ORDER BY snapshot_at, source_file
        ) AS previous_impressions
    FROM google_ads_placements
)
SELECT
    platform,
    placement_name,
    placement_url,
    placement_type,
    report_date,
    source_file,
    snapshot_at,
    previous_source_file,
    previous_snapshot_at,
    previous_impressions,
    impressions AS current_impressions,
    impressions - previous_impressions AS change_amount,
    CASE
        WHEN previous_impressions IS NULL THEN NULL
        ELSE previous_impressions - impressions
    END AS drop_amount,
    CASE
        WHEN previous_impressions IS NULL OR previous_impressions = 0 THEN NULL
        ELSE ROUND(((impressions - previous_impressions)::numeric / previous_impressions) * 100, 2)
    END AS change_percent,
    CASE
        WHEN previous_impressions IS NULL OR previous_impressions = 0 THEN NULL
        ELSE ROUND(((previous_impressions - impressions)::numeric / previous_impressions) * 100, 2)
    END AS drop_percent
FROM ordered_snapshots
WHERE previous_impressions IS NOT NULL;
