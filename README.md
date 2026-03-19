# 🎂 Birthday Reminder — Automated Notification Pipeline

> An end-to-end ETL pipeline that transforms a static Excel dataset into automated, real-time birthday notifications — orchestrated on Apache Airflow, delivered via Telegram. Zero human intervention after deployment.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Apache Airflow DAG                         │
│            Schedule: 0 9 * * *  (daily 09:00 AM)           │
└──────────────────────┬──────────────────────────────────────┘
                       │
              ┌────────▼────────┐
              │    EXTRACT       │   pandas.read_excel()
              │  birthday_data  │   75 birthday records
              │     .xlsx       │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │   TRANSFORM      │   Date arithmetic
              │  Week scan       │   Mon–Sun window (7 days)
              │  Classify:       │   missed / today / upcoming
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │     LOAD         │   Telegram Bot API
              │  Push notify     │   REST GET request
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  Random Quote    │   ZenQuotes API
              │  (bonus task)    │   logged to Airflow
              └─────────────────┘

Task chain:  check_birthdays  ──►  print_random_quote
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | Apache Airflow 2.x |
| Language | Python 3.8+ |
| Data Ingestion | Pandas `read_excel` |
| Scheduling | Cron via Airflow |
| Notification | Telegram Bot API (REST) |
| Runtime | Linux / WSL2 |

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/birthday-reminder.git
cd birthday-reminder
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure credentials

```bash
cp .env.example .env
# Edit .env and fill in your Telegram token and chat ID
```

### 4. Set Airflow home to this project

```bash
export AIRFLOW_HOME=$(pwd)
```

### 5. Initialise the Airflow database

```bash
airflow db init
airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com
```

### 6. Start services (two terminals)

```bash
# Terminal 1
airflow scheduler

# Terminal 2
airflow webserver --port 8080
```

### 7. Open the UI

```
http://localhost:8080
```

Unpause the `birthday_reminder` DAG and trigger it manually to test.

---

## Standalone Test (no Airflow needed)

```bash
python3 tests/test_birthday.py
```

This runs the full ETL logic — Excel ingestion → birthday classification → Telegram delivery — without starting any Airflow service.

---

## Project Structure

```
birthday-reminder/
├── dags/
│   ├── birthday_reminder.py    ← Airflow DAG (pipeline definition)
│   └── birthday_data.xlsx      ← Birthday data source
├── tests/
│   └── test_birthday.py        ← Standalone test (no Airflow needed)
├── .env.example                ← Credential template
├── .gitignore
├── requirements.txt
├── README.md
├── PORTFOLIO.md                ← Detailed portfolio writeup
└── TESTING_GUIDE.md            ← Step-by-step testing walkthrough
```

---

## How It Works

1. **Extract** — Reads `birthday_data.xlsx` with Pandas. File path is resolved dynamically so the pipeline is portable across machines.

2. **Transform** — Scans the full current week (Monday to Sunday). Each matching birthday is classified into one of three states:
   - `missed` — birthday was earlier this week
   - `today` — birthday is today
   - `upcoming` — birthday is later this week

3. **Load** — Each classified message is pushed to Telegram via the Bot API. If anything fails, the error is caught and sent to Telegram immediately — no silent failures.

---

## Skills Demonstrated

- Apache Airflow DAG design and multi-task orchestration
- ETL pipeline with Pandas, REST API integration, and cron scheduling
- Temporal window analysis and classification logic
- Production patterns: env-var credentials, graceful error handling, structured logging
- Standalone test script separate from orchestration layer

---

## What I Would Build Next

| Enhancement | Why |
|---|---|
| PostgreSQL / BigQuery backend | Replace Excel for concurrent writes and query performance |
| dbt transformation layer | Version-controlled, testable SQL for classification logic |
| Monitoring dashboard (Grafana) | Visualise pipeline health and delivery metrics |
| Multi-channel delivery | Slack, WhatsApp, or email based on user preference |
| Data quality checks | Validate null dates and duplicates before processing |

---

## Setup Guide

See **[TESTING_GUIDE.md](TESTING_GUIDE.md)** for the complete step-by-step walkthrough — from first clone to verified automated runs.

---

## Portfolio

See **[PORTFOLIO.md](PORTFOLIO.md)** for the full technical writeup — architecture decisions, engineering trade-offs, results metrics, and skills breakdown.
