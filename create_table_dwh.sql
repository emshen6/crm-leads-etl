-- ============================================================
-- Таблица: stg.crm_leads
-- Слой:    STG (staging) — «сырые» данные из CRM, без трансформаций
-- ============================================================
-- Соглашение об именах колонок:
--   * snake_case, нижний регистр — стандарт PostgreSQL / SQL-аналитики
--   * без префикса «UF_» (пользовательское поле Bitrix) — не несёт аналитической ценности
--   * «primary» в названиях phone_primary / email_primary означает
--     «основной контакт для связи» (выбирается по VALUE_TYPE = 'WORK')
-- ============================================================

CREATE SCHEMA IF NOT EXISTS stg;

CREATE TABLE IF NOT EXISTS stg.crm_leads (
    lead_id             BIGINT          NOT NULL,

    -- Тема / название лида — свободный текст, TEXT без ограничения длины
    title               TEXT,

    -- Имя и фамилия контакта; разделены для удобства поиска и сортировки
    first_name          TEXT,
    last_name           TEXT,

    -- Статус воронки (NEW, IN_PROCESS, PROCESSED и т.д.)
    -- TEXT, а не ENUM: новые статусы из CRM не должны ломать загрузку
    status_id           TEXT,

    -- Канал привлечения (WEBFORM, CALL, PARTNER, EMAIL, SOCIAL)
    source_id           TEXT,

    -- Сегмент клиента (VIP, Обычный, Потенциальный)
    client_type         TEXT,

    -- Предпочтительный способ связи (Email, Телефон, WhatsApp)
    contact_method      TEXT,

    -- Основной телефон — берётся WORK-тип, иначе первый из массива
    phone_primary       TEXT,
    -- Тип телефона (WORK / MOBILE / HOME) — нужен для анализа каналов
    phone_primary_type  TEXT,

    -- Основной email — аналогично телефону
    email_primary       TEXT,
    email_primary_type  TEXT,

    -- Служебное поле: метка времени загрузки строки; помогает отследить
    -- момент появления данных в хранилище (аудит, дебаг)
    loaded_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT crm_leads_pkey PRIMARY KEY (lead_id)
);

-- Индексы для типичных аналитических запросов
CREATE INDEX IF NOT EXISTS crm_leads_status_idx  ON stg.crm_leads (status_id);
CREATE INDEX IF NOT EXISTS crm_leads_source_idx  ON stg.crm_leads (source_id);
CREATE INDEX IF NOT EXISTS crm_leads_loaded_idx  ON stg.crm_leads (loaded_at);

COMMENT ON TABLE  stg.crm_leads                      IS 'Staging-слой: лиды из CRM (raw), загружаются через etl_leads.py';
COMMENT ON COLUMN stg.crm_leads.lead_id              IS 'ID лида в CRM (первичный ключ)';
COMMENT ON COLUMN stg.crm_leads.title                IS 'Тема лида';
COMMENT ON COLUMN stg.crm_leads.first_name           IS 'Имя контакта';
COMMENT ON COLUMN stg.crm_leads.last_name            IS 'Фамилия контакта';
COMMENT ON COLUMN stg.crm_leads.status_id            IS 'Статус воронки (NEW / IN_PROCESS / PROCESSED)';
COMMENT ON COLUMN stg.crm_leads.source_id            IS 'Канал привлечения';
COMMENT ON COLUMN stg.crm_leads.client_type          IS 'Сегмент клиента';
COMMENT ON COLUMN stg.crm_leads.contact_method       IS 'Предпочтительный способ связи';
COMMENT ON COLUMN stg.crm_leads.phone_primary        IS 'Основной телефон (VALUE_TYPE=WORK, иначе первый)';
COMMENT ON COLUMN stg.crm_leads.phone_primary_type   IS 'Тип основного телефона (WORK/MOBILE/HOME)';
COMMENT ON COLUMN stg.crm_leads.email_primary        IS 'Основной email (VALUE_TYPE=WORK, иначе первый)';
COMMENT ON COLUMN stg.crm_leads.email_primary_type   IS 'Тип основного email (WORK/HOME)';
COMMENT ON COLUMN stg.crm_leads.loaded_at            IS 'Метка времени загрузки строки в DWH';
