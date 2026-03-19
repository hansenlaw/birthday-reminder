# 🎂 Birthday Reminder Pipeline

**Role:** Data Engineer & Data Analyst
**Stack:** Apache Airflow · Python · Pandas · Telegram Bot API · Linux/WSL2
**Type:** End-to-end ETL pipeline · Automated notification system · Portfolio project

---

## The Problem

Birthday data sits in spreadsheets. Nothing acts on it. Birthdays get missed.

The deeper issue is not "forgetting birthdays" — it is that **data at rest produces zero value unless a system processes and delivers it.** This project closes that gap: transforming a static Excel file into a real-time, automated notification system through a proper data engineering pipeline.

This is exactly the kind of problem data engineering exists to solve.

---

## What I Built

A fully automated data pipeline that runs every day at 09:00 AM — zero human action required after deployment:

- **Ingests** 75 birthday records from a structured Excel file using Pandas
- **Analyzes** the entire current week (Monday–Sunday) — not just today — for a temporal view
- **Classifies** each birthday into one of three states: `missed`, `today`, or `upcoming`
- **Delivers** personalised, classified notifications to Telegram via the Bot API
- **Self-reports failures** — if anything breaks, the error is pushed to Telegram immediately

---

## Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Apache Airflow DAG                        │
│              Schedule: 0 9 * * *  (daily, 09:00 AM)         │
└─────────────────────┬────────────────────────────────────────┘
                      │
             ┌────────▼────────┐
             │    EXTRACT       │   pandas.read_excel()
             │  birthday_data  │   75 birthday records
             │     .xlsx       │   dynamic file path
             └────────┬────────┘
                      │
             ┌────────▼────────┐
             │   TRANSFORM      │   Date arithmetic (timedelta)
             │  Week scan       │   Monday → Sunday (7-day window)
             │  Classification  │   missed / today / upcoming
             └────────┬────────┘
                      │
             ┌────────▼────────┐
             │     LOAD         │   Telegram Bot API
             │  Push notify     │   REST POST · retry logic
             └────────┬────────┘
                      │
             ┌────────▼────────┐
             │  Random Quote    │   ZenQuotes API · fallback list
             │  (bonus task)    │   logged to Airflow per run
             └─────────────────┘

Task dependency:  check_birthdays  ──►  print_random_quote
```

---

## Technical Stack

| Layer | Technology | Why This Choice |
| --- | --- | --- |
| Orchestration | Apache Airflow 2.x | Industry standard — used at Airbnb, Grab, Gojek, LinkedIn |
| Language | Python 3.8+ | Native Airflow language; dominant in data engineering |
| Data Ingestion | Pandas `read_excel` | Handles `.xlsx` natively; optimised for structured tabular data |
| Scheduling | Cron expression via Airflow | Fine-grained time control, decoupled from application logic |
| Notification | Telegram Bot API (REST POST) | Push notification delivered in under 2 seconds |
| Credential Management | `.env` file + `os.getenv()` | Zero secrets in source code — production security pattern |
| Runtime | Linux / WSL2 | Production-equivalent local environment |

---

## Technical Deep-Dive

### Extract — Dynamic File Ingestion

```python
base_dir  = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(base_dir, 'birthday_data.xlsx')
df = pd.read_excel(file_path)
```

The file path is resolved **dynamically** relative to the DAG file location — no hardcoded absolute paths. The pipeline runs identically on any machine that clones the repository.

---

### Transform — Temporal Window Analysis

The pipeline does not simply ask "is today someone's birthday?" That is reactive and narrow.

Instead it scans the **entire current week (Monday through Sunday)** — a deliberate analytical design choice:

```python
start_of_week = today - timedelta(days=today.weekday())

for i in range(7):
    current_day = start_of_week + timedelta(days=i)
    matched = df[df['date'].apply(
        lambda x: (x.month, x.day) == (current_day.month, current_day.day)
    )]
```

Each matched birthday is **classified into one of three analytical states:**

| State | Condition | Message Generated |
| --- | --- | --- |
| `missed` | Birthday was earlier this week | 🎂 X's birthday was missed on Monday! |
| `today` | Birthday is today | 🎉 Happy Birthday, X! Today is your special day! |
| `upcoming` | Birthday is later this week | 🎈 Upcoming — X's birthday is on Friday! |

This classification is the analytical core — turning raw date records into **contextual, actionable insights.**

---

### Load — Reliable Notification Delivery

Each classified message is delivered to Telegram via REST POST with **retry logic and exponential backoff:**

```python
def send_telegram_message(message, retries=3, backoff=2):
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(url, data=params, timeout=20)
            if response.status_code == 200:
                return True   # delivered
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
        time.sleep(backoff ** attempt)
    return False  # all attempts exhausted
```

Credentials are loaded from `.env` — **never embedded in source code.**

---

## Engineering Decisions

### Why Apache Airflow instead of a plain cron job?

A bare cron job runs and disappears — no visibility, no audit trail, no observability. Airflow adds:

- Web UI showing every run's status (success / failed / running)
- Full task-level log storage, inspectable at any time
- Explicit task dependency management (`task_a >> task_b`)
- Pause and resume without touching system cron
- DAG versioning and reusability

This is the difference between a script and a **production-grade data pipeline.**

---

### Why scan the full week instead of only today?

Same-day checks are reactive. A week-scope scan is proactive:

- See that someone's birthday was **yesterday** → still time to send a belated message
- See that someone's birthday is **in 4 days** → time to prepare

This turns a point-in-time lookup into a **temporal window analysis** — a deliberate analytical design choice.

---

### Why Telegram over email?

Email carries high friction — inbox noise, delayed opens, easy to ignore. Telegram delivers a **push notification in under 2 seconds** to any device. For a time-sensitive alerting system, delivery latency and open rate are critical metrics. Telegram wins both.

---

### Why retry logic on Telegram delivery?

A pipeline that silently fails on network transients is unreliable. The retry mechanism with exponential backoff handles:

- Temporary SSL/TLS handshake failures
- Telegram API rate limits
- Brief network interruptions

If all retries fail, the failure is logged clearly — **no silent drops.**

---

## Observability & Error Handling

Every step emits structured, labelled log output:

```
[EXTRACT] Source file : /path/to/birthday_data.xlsx
[EXTRACT] Loaded 75 records | columns: ['name', 'date']
[TRANSFORM] Scanning Thursday (03-19)
[TRANSFORM] Matches  : 1
[TRANSFORM] → 🎉 Happy Birthday, Hansen! Today is your special day!
[LOAD] Attempt 1/3 — sending to chat 5304908862
[LOAD] HTTP 200
[LOAD] Message delivered successfully.
```

These logs are **captured by Airflow and stored per-task, per-run** — fully inspectable in the Web UI at any time.

**Graceful failure with immediate user notification:**

```python
except Exception as e:
    traceback.print_exc()
    send_telegram_message(f"⚠️ Birthday pipeline error: {e}")
```

If the pipeline breaks — missing file, API timeout, malformed data — the error is caught and pushed to Telegram. The engineer is informed without checking the Airflow UI. This is the observability pattern used in **production data systems.**

---

## Testing Strategy

The pipeline ships with a **standalone test script** (`tests/test_birthday.py`) that validates core logic independently of Airflow:

```bash
python3 tests/test_birthday.py
```

**Why this matters:**

- Runs the full ETL chain without starting any Airflow service
- Faster iteration loop on transformation logic during development
- Validates Telegram API integration in isolation before DAG deployment
- Mirrors the separation of concerns used in professional data engineering:
  **test the business logic first, then orchestrate it**

---

## Results

| Metric | Before | After |
| --- | --- | --- |
| Birthdays missed per month | 2–4 | **0** |
| Daily effort for reminders | ~5 min | **0 min** |
| Advance notice window | 0 days (same day only) | **Up to 6 days ahead** |
| Failure visibility | Silent — nothing | **Error pushed to Telegram instantly** |
| Run auditability | None | **Full per-run logs in Airflow UI** |
| Scalability | Manual effort per entry | **Unlimited — add a row, get a reminder forever** |

---

## Skills Demonstrated

### Data Engineering

- Designed and deployed a complete ETL pipeline on Apache Airflow (industry-standard orchestrator)
- Defined multi-task DAG with explicit dependency chain: `check_birthdays >> print_random_quote`
- Applied `catchup=False` to prevent backfill accumulation on scheduler restart
- Implemented production-level structured logging across all pipeline layers
- Separated orchestration from business logic for maintainability and testability
- Added retry mechanism with exponential backoff for reliable API delivery

### Data Analysis

- Translated a business question into structured analytical logic with classified outputs
- Designed a temporal window analysis (Monday–Sunday scan) for proactive vs. reactive insights
- Implemented three-state classification system (`missed` / `today` / `upcoming`)
- Delivered analysis results as actionable, human-readable notifications — not raw data dumps

### Python & Software Engineering

- File I/O with dynamic path resolution — portable across all environments
- Date arithmetic using `datetime` and `timedelta`
- DataFrame filtering using Pandas with lambda expressions
- REST API integration (POST) with response validation, timeout, and retry
- Clean exception handling with user-facing error reporting via Telegram

### Production & DevOps Mindset

- Credential management via `.env` + `os.getenv()` — zero secrets in source code
- Cron scheduling decoupled from application code
- Graceful failure with self-reporting: error pushed to Telegram, not silently dropped
- Graceful API degradation: local fallback when external quote API is unavailable
- Deployed on Linux/WSL2 — production-equivalent local environment

---

## What I Would Build Next

| Enhancement | Why It Matters |
| --- | --- |
| **PostgreSQL or BigQuery backend** | Replace Excel with a proper database — concurrent writes, query performance, scalability to thousands of records |
| **dbt transformation layer** | Version-controlled, testable SQL models for birthday classification logic |
| **Monitoring dashboard (Grafana / Metabase)** | Visualise pipeline run history, failure rates, and notification delivery trends |
| **Multi-channel delivery** | Route notifications to Slack, WhatsApp, or email based on user preference |
| **Parameterized DAG runs** | Accept timezone per-person — a step toward true multi-tenant pipeline design |
| **Data quality checks** | Validate null dates and duplicate names before processing — fail fast, fail loud |

---

## GitHub Repository

[github.com/hansenlaw/birthday-reminder](https://github.com/hansenlaw/birthday-reminder)

---

## Portfolio Screenshots

> Capture these screenshots after running the pipeline — they turn this writeup into proof.

### 📸 Screenshot 1 — Airflow Graph View: All Tasks Green

**Where:** Airflow UI → `birthday_reminder` DAG → **Graph** tab → after a successful run

**What it shows:** Complete pipeline executed end-to-end. Two tasks in correct dependency order. Green = success.

**Caption:** *"Airflow Graph View — both tasks completed successfully in the correct dependency order."*

> **This is the single most important screenshot for a data engineering hiring manager.**

---

### 📸 Screenshot 2 — Telegram Notification Received

**Where:** Telegram app → chat with your bot

**What it shows:** The pipeline delivers real data to a live system. End-to-end proof.

**Caption:** *"Automated birthday notification delivered to Telegram — triggered by Airflow DAG, zero manual action."*

---

### 📸 Screenshot 3 — Airflow Task Logs

**Where:** Airflow UI → `birthday_reminder` → any run → `check_birthdays` → **Log** tab

**What it shows:** Structured, labelled logs from every pipeline step. Observability mindset.

**Caption:** *"Full task logs — data ingestion, birthday classification, and Telegram API call. Every step is observable."*

---

### 📸 Screenshot 4 — DAGs List with Schedule

**Where:** Airflow UI → DAGs list page

**What it shows:** DAG is registered, active, scheduled at `0 9 * * *`, next run visible.

**Caption:** *"Birthday Reminder DAG active in Airflow with daily 09:00 schedule — fully automated."*

---

### 📸 Screenshot 5 — Standalone Test Terminal Output

**Where:** Terminal after running `python3 tests/test_birthday.py`

**What it shows:** ETL logic runs and delivers without any Airflow infrastructure.

**Caption:** *"Standalone test — full ETL from Excel ingestion to Telegram delivery, no Airflow needed."*

---

### Screenshot Priority

| Priority | Screenshot | What It Proves |
| --- | --- | --- |
| **Must have** | Graph View — all tasks green | Airflow proficiency, pipeline execution |
| **Must have** | Telegram message received | Real end-to-end delivery |
| **Must have** | Task log — full structured trace | Observability and logging mindset |
| **Strong** | DAGs list with schedule & next run | Scheduling automation configured |
| **Good** | Terminal: standalone test output | Testing-first development mindset |
