CREATE SCHEMA IF NOT EXISTS stg;

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

CREATE INDEX IF NOT EXISTS crm_leads_status_idx  ON stg.crm_leads (status_id);
CREATE INDEX IF NOT EXISTS crm_leads_source_idx  ON stg.crm_leads (source_id);
CREATE INDEX IF NOT EXISTS crm_leads_loaded_idx  ON stg.crm_leads (loaded_at);
