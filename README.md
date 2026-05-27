# CRM Leads ETL

Загрузка лидов из CRM API в PostgreSQL (слой `stg.crm_leads`).  
Реализовано в двух вариантах: standalone-скрипт и Airflow DAG.

## Структура проекта

```
├── etl_leads.py          # Standalone ETL-скрипт (запуск вручную / из cron)
├── dag_crm_leads.py      # Airflow DAG (ежедневно в 06:00 UTC)
├── create_table_dwh.sql  # DDL: схема stg + таблица crm_leads + индексы
├── requirements.txt      # Python-зависимости
└── .env                  # Переменные окружения (в репозиторий не включён)
```

## Источник данных

API-эндпоинт возвращает массив CRM-лидов. Каждый лид содержит вложенные массивы `PHONE` и `EMAIL`.  
Стратегия уплощения: одна строка на лид, выбирается контакт с `VALUE_TYPE = 'WORK'`, иначе первый из массива.

## Таблица `stg.crm_leads`

| Колонка              | Тип         | Описание                                      |
|----------------------|-------------|-----------------------------------------------|
| `lead_id`            | BIGINT (PK) | ID лида в CRM                                 |
| `title`              | TEXT        | Тема лида                                     |
| `first_name`         | TEXT        | Имя контакта                                  |
| `last_name`          | TEXT        | Фамилия контакта                              |
| `status_id`          | TEXT        | Статус воронки (NEW / IN_PROCESS / PROCESSED) |
| `source_id`          | TEXT        | Канал привлечения                             |
| `client_type`        | TEXT        | Сегмент клиента                               |
| `contact_method`     | TEXT        | Предпочтительный способ связи                 |
| `phone_primary`      | TEXT        | Основной телефон                              |
| `phone_primary_type` | TEXT        | Тип телефона (WORK / MOBILE / HOME)           |
| `email_primary`      | TEXT        | Основной email                                |
| `email_primary_type` | TEXT        | Тип email (WORK / HOME)                       |
| `loaded_at`          | TIMESTAMPTZ | Метка времени загрузки в DWH                  |

Стратегия записи: **upsert** (`ON CONFLICT (lead_id) DO UPDATE`) — повторный запуск идемпотентен.

## Установка

```bash
pip install -r requirements.txt
```

Создать файл `.env` (или задать переменные окружения):

```env
PG_HOST=localhost
PG_PORT=5432
PG_DB=meo_dwh
PG_USER=postgres
PG_PASSWORD=postgres
```

## Запуск (standalone)

```bash
# Создать таблицу (один раз)
psql -d meo_dwh -f create_table_dwh.sql

# Запустить ETL
python etl_leads.py
```

## Запуск (Airflow)

1. Скопировать `dag_crm_leads.py` в папку `dags/` Airflow.
2. Создать Airflow-коннекшн `postgres_meo_dwh` (Admin → Connections).
3. DAG запускается автоматически каждый день в **06:00 UTC**.
