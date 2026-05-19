import json
import os
from io import StringIO
from datetime import datetime

import boto3
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

PLATFORM = os.getenv('PLATFORM', 'google-ads')
SECRET_NAME = os.getenv('SECRET_NAME', 'example/google-ads/postgres')

_db_credentials = None
_s3_client = None
_secrets_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client('s3')
    return _s3_client


def get_secrets_client():
    global _secrets_client
    if _secrets_client is None:
        _secrets_client = boto3.client('secretsmanager')
    return _secrets_client


def get_db_credentials():
    global _db_credentials
    if _db_credentials is not None:
        return _db_credentials

    response = get_secrets_client().get_secret_value(SecretId=SECRET_NAME)
    _db_credentials = json.loads(response['SecretString'])
    return _db_credentials


def lambda_handler(event, context):
    try:
        bucket_name, file_key = get_s3_file_from_event(event)

        if not file_key.startswith(f'{PLATFORM}/uploads/'):
            return {'statusCode': 400, 'body': 'File uploaded to wrong folder'}

        csv_text = download_csv_from_s3(bucket_name, file_key)
        rows = parse_google_ads_csv(csv_text, file_key)

        if not rows.empty:
            save_rows(rows)

        move_to_processed(bucket_name, file_key)

        print(f"Processed {len(rows)} rows from {file_key}")
        return {'statusCode': 200, 'body': json.dumps(f'Processed {len(rows)} rows')}

    except Exception as exc:
        print(f"Error: {str(exc)}")
        return {'statusCode': 500, 'body': json.dumps(f'Error: {str(exc)}')}


def get_s3_file_from_event(event):
    s3_event = event['Records'][0]['s3']
    return s3_event['bucket']['name'], s3_event['object']['key']


def download_csv_from_s3(bucket_name, file_key):
    response = get_s3_client().get_object(Bucket=bucket_name, Key=file_key)
    return response['Body'].read().decode('utf-8')


def get_report_date(date_line):
    clean_line = date_line.strip().strip('"')
    start_date = clean_line.split(' - ')[0].strip().rstrip(',')
    return datetime.strptime(start_date, '%B %d, %Y').date()


def parse_google_ads_csv(csv_content, file_key):
    lines = csv_content.strip().split('\n')
    if len(lines) < 3:
        raise ValueError(f"CSV has only {len(lines)} lines, expected at least 3")

    report_date = get_report_date(lines[1])
    data_rows = '\n'.join(lines[2:])
    rows = pd.read_csv(StringIO(data_rows), dtype={'Impr.': 'Int64'})
    rows = rows.dropna(how='all')

    rows = rows.rename(columns={
        'Performance Max placement': 'placement_name',
        'Performance Max placement URL': 'placement_url',
        'Performance Max placement type': 'placement_type',
        'Impr.': 'impressions',
    })

    needed_columns = {'placement_name', 'placement_url', 'placement_type', 'impressions'}
    missing_columns = needed_columns - set(rows.columns)
    if missing_columns:
        raise ValueError(f"Missing expected columns: {sorted(missing_columns)}")

    now = datetime.utcnow()
    rows['placement_type'] = rows['placement_type'].str.strip().replace('--', 'Unspecified')
    rows['impressions'] = rows['impressions'].fillna(0).astype(int)
    rows['platform'] = PLATFORM
    rows['report_date'] = report_date
    rows['source_file'] = file_key
    rows['snapshot_at'] = now
    rows['uploaded_at'] = now

    return rows


def get_db_connection():
    creds = get_db_credentials()
    return psycopg2.connect(
        host=creds['host'],
        port=creds.get('port', 5432),
        database=creds.get('dbname', 'campaign_data'),
        user=creds['username'],
        password=creds['password'],
    )


def save_rows(rows):
    conn = get_db_connection()
    try:
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
        cur.close()
    finally:
        conn.close()


def move_to_processed(bucket_name, file_key):
    new_key = file_key.replace('/uploads/', '/processed/')
    get_s3_client().copy_object(
        Bucket=bucket_name,
        CopySource={'Bucket': bucket_name, 'Key': file_key},
        Key=new_key,
    )
    get_s3_client().delete_object(Bucket=bucket_name, Key=file_key)
