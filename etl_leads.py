"""
Задание 4: Загрузка данных из API в PostgreSQL.
Эндпоинт возвращает CRM-лиды с вложенными массивами PHONE и EMAIL.
Стратегия уплощения: одна строка на лид, берём первый телефон и первый email
(по признаку VALUE_TYPE = 'WORK', иначе первый попавшийся).
"""

import logging
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()
import psycopg2.extras
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

API_URL = "https://run.mob-edu.ru/webhook/da-test-sample"

DB_CONFIG = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": int(os.getenv("PG_PORT", 5432)),
    "dbname": os.getenv("PG_DB", "meo_dwh"),
    "user": os.getenv("PG_USER", "postgres"),
    "password": os.getenv("PG_PASSWORD", "postgres"),
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS stg.crm_leads (
    lead_id             BIGINT          NOT NULL,
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


def pick_contact(items: list[dict], preferred_type: str = "WORK") -> tuple[str | None, str | None]:
    if not items:
        return None, None
    preferred = next((i for i in items if i.get("VALUE_TYPE") == preferred_type), None)
    chosen = preferred or items[0]
    return chosen.get("VALUE"), chosen.get("VALUE_TYPE")


def flatten(raw: dict) -> tuple:
    phone_val, phone_type = pick_contact(raw.get("PHONE", []))
    email_val, email_type = pick_contact(raw.get("EMAIL", []))
    return (
        int(raw["ID"]),
        raw.get("TITLE"),
        raw.get("NAME"),
        raw.get("LAST_NAME"),
        raw.get("STATUS_ID"),
        raw.get("SOURCE_ID"),
        raw.get("UF_CLIENT_TYPE"),
        raw.get("UF_CONTACT_METHOD"),
        phone_val,
        phone_type,
        email_val,
        email_type,
    )


def fetch_leads() -> list[dict]:
    log.info("Fetching %s", API_URL)
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def load_to_db(rows: list[tuple]) -> None:
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("CREATE SCHEMA IF NOT EXISTS stg;")
                cur.execute(CREATE_TABLE_SQL)
                psycopg2.extras.execute_values(cur, UPSERT_SQL, rows)
                log.info("Upserted %d rows", len(rows))
    finally:
        conn.close()


def main() -> None:
    raw_leads = fetch_leads()
    log.info("Received %d leads", len(raw_leads))
    rows = [flatten(lead) for lead in raw_leads]
    load_to_db(rows)
    log.info("Done")


if __name__ == "__main__":
    main()
