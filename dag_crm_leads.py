from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

import requests
import psycopg2.extras

API_URL = "https://run.mob-edu.ru/webhook/da-test-sample"
POSTGRES_CONN_ID = "postgres_meo_dwh"

CREATE_TABLE_SQL = """
CREATE SCHEMA IF NOT EXISTS stg;
CREATE TABLE IF NOT EXISTS stg.crm_leads (
    lead_id             INTEGER         NOT NULL,
    title               TEXT,
    first_name          TEXT,
    last_name           TEXT,
    status_id           TEXT,
    source_id           TEXT,
    client_type         TEXT,
    contact_method      TEXT,
    phone_primary       TEXT,
    phone_primary_type  TEXT,
    email_primary       TEXT,
    email_primary_type  TEXT,
    loaded_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT crm_leads_pkey PRIMARY KEY (lead_id)
);
"""

UPSERT_SQL = """
INSERT INTO stg.crm_leads (
    lead_id, title, first_name, last_name,
    status_id, source_id, client_type, contact_method,
    phone_primary, phone_primary_type,
    email_primary, email_primary_type
) VALUES %s
ON CONFLICT (lead_id) DO UPDATE SET
    title               = EXCLUDED.title,
    first_name          = EXCLUDED.first_name,
    last_name           = EXCLUDED.last_name,
    status_id           = EXCLUDED.status_id,
    source_id           = EXCLUDED.source_id,
    client_type         = EXCLUDED.client_type,
    contact_method      = EXCLUDED.contact_method,
    phone_primary       = EXCLUDED.phone_primary,
    phone_primary_type  = EXCLUDED.phone_primary_type,
    email_primary       = EXCLUDED.email_primary,
    email_primary_type  = EXCLUDED.email_primary_type,
    loaded_at           = NOW();
"""


def _pick_contact(items: list[dict], preferred_type: str = "WORK") -> tuple[str | None, str | None]:
    if not items:
        return None, None
    preferred = next((i for i in items if i.get("VALUE_TYPE") == preferred_type), None)
    chosen = preferred or items[0]
    return chosen.get("VALUE"), chosen.get("VALUE_TYPE")


def fetch_and_load(**context) -> None:
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()
    raw_leads = resp.json()

    rows = []
    for raw in raw_leads:
        phone_val, phone_type = _pick_contact(raw.get("PHONE", []))
        email_val, email_type = _pick_contact(raw.get("EMAIL", []))
        rows.append((
            int(raw["ID"]),
            raw.get("TITLE"),
            raw.get("NAME"),
            raw.get("LAST_NAME"),
            raw.get("STATUS_ID"),
            raw.get("SOURCE_ID"),
            raw.get("UF_CLIENT_TYPE"),
            raw.get("UF_CONTACT_METHOD"),
            phone_val, phone_type,
            email_val, email_type,
        ))

    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    conn = hook.get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
            psycopg2.extras.execute_values(cur, UPSERT_SQL, rows)

    print(f"Upserted {len(rows)} rows into stg.crm_leads")


default_args = {
    "owner": "data_team",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="crm_leads_to_dwh",
    description="Загрузка CRM-лидов из API в stg.crm_leads",
    schedule_interval="0 6 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["crm", "stg", "etl"],
) as dag:

    load_leads = PythonOperator(
        task_id="fetch_and_load_leads",
        python_callable=fetch_and_load,
    )
