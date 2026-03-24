# Birthday Reminder — Automated Notification Pipeline

[![Daily Run](https://github.com/hansenlaw/birthday-reminder/actions/workflows/birthday-daily.yml/badge.svg)](https://github.com/hansenlaw/birthday-reminder/actions/workflows/birthday-daily.yml)

> End-to-end ETL pipeline that reads a birthday spreadsheet every morning, classifies birthdays for the full week, and pushes personalised notifications to Telegram. Built on Apache Airflow. Runs daily on GitHub Actions — no server needed.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Apache Airflow DAG                         │
│            Schedule: 0 9 * * *  (daily 09:00 WIB)          │
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
              │  Push notify     │   REST POST · retry logic
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
| Scheduling | Cron via Airflow / GitHub Actions |
| Notification | Telegram Bot API (REST) |
| Runtime | Linux / WSL2 / GitHub Actions |

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/hansenlaw/birthday-reminder.git
cd birthday-reminder
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure credentials

```bash
cp .env.example .env
# Edit .env and fill in your Telegram bot token and chat ID
```

### 4. Test immediately (no Airflow needed)

```bash
python3 tests/test_birthday.py
```

This runs the full ETL pipeline — Excel ingestion to Telegram delivery — in one command.

---

## Run with Airflow

### Set Airflow home

```bash
export AIRFLOW_HOME=$(pwd)
```

### Initialise the database

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

### Start services (two terminals)

```bash
# Terminal 1
airflow scheduler

# Terminal 2
airflow webserver --port 8080
```

Open `http://localhost:8080`, unpause the `birthday_reminder` DAG, and trigger it manually to test.

---

## Run on GitHub Actions (no local setup needed)

The pipeline also runs on GitHub Actions — no Airflow installation required.

**Setup:**
1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Add two secrets:
   - `TELEGRAM_BOT_TOKEN` — your bot token from @BotFather
   - `TELEGRAM_CHAT_ID` — your numeric chat ID
3. The workflow runs automatically every day at **09:00 WIB**

You can also trigger it manually from the **Actions** tab at any time.

---

## Project Structure

```
birthday-reminder/
├── .github/
│   └── workflows/
│       └── birthday-daily.yml  ← GitHub Actions daily schedule
├── dags/
│   ├── birthday_reminder.py    ← Airflow DAG (pipeline definition + all logic)
│   └── birthday_data.xlsx      ← Birthday data source (75 records)
├── tests/
│   └── test_birthday.py        ← Standalone test — runs without Airflow
├── .env.example                ← Credential template (safe to commit)
├── .gitignore
├── requirements.txt
├── README.md
├── PORTFOLIO.md                ← Full technical writeup
└── walkthrough.md              ← Complete guide: build from zero to production
```

---

## How It Works

**Extract** — Reads `birthday_data.xlsx` with Pandas. The file path is resolved dynamically relative to the script, so it works on any machine.

**Transform** — Scans the full current week (Monday to Sunday). Each matching birthday is classified:
- `missed` — birthday was earlier this week
- `today` — birthday is today
- `upcoming` — birthday is later this week

**Load** — Each classified message is pushed to Telegram via REST POST with retry logic and exponential backoff. If anything fails, the error is caught and sent to Telegram — no silent failures.

---

## Skills Demonstrated

- Apache Airflow DAG design and multi-task orchestration
- ETL pipeline with Pandas, REST API integration, cron scheduling
- Temporal window analysis and three-state classification logic
- Production patterns: env-var credentials, retry with backoff, structured logging
- Standalone test script decoupled from orchestration layer
- GitHub Actions CI/CD for automated daily execution

---

## What I Would Build Next

| Enhancement | Why |
|---|---|
| PostgreSQL / BigQuery backend | Replace Excel for concurrent writes and query performance |
| dbt transformation layer | Version-controlled, testable SQL for classification logic |
| Monitoring dashboard (Grafana) | Visualise pipeline health and delivery trends |
| Multi-channel delivery | Slack, WhatsApp, or email based on preference |
| Data quality checks | Validate null dates and duplicates before processing |

---

## Documentation

**[walkthrough.md](walkthrough.md)** — Complete guide to understanding and rebuilding this project from scratch. Covers every file, every function, every decision.

**[PORTFOLIO.md](PORTFOLIO.md)** — Full technical writeup with architecture decisions, engineering trade-offs, and results metrics.
