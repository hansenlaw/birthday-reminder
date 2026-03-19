# Birthday Reminder Pipeline — Portfolio

> **End-to-end ETL pipeline** that transforms a static Excel dataset into automated, real-time birthday intelligence — orchestrated on Apache Airflow, delivered via Telegram. Zero human intervention after deployment.

---

## The Problem

Birthday data sits in spreadsheets. Nothing acts on it. Birthdays get missed.

The deeper issue is not "forgetting birthdays" — it is that **data at rest produces zero value unless a system processes and delivers it**. This project closes that gap: turning passive, structured data into time-aware, automated notifications through a proper data pipeline.

This is exactly the kind of problem data engineering exists to solve.

---

## What I Built

A fully automated data pipeline that runs every day at 09:00 AM:

1. **Ingests** birthday records from a structured Excel file using Pandas
2. **Analyzes** the entire current week — not just today — for a temporal view
3. **Classifies** each birthday into one of three states: `missed`, `today`, or `upcoming`
4. **Delivers** personalized, classified notifications to Telegram via the Bot API
5. **Self-reports failures** — if anything breaks, the error is pushed to Telegram immediately

---

## Pipeline Architecture (ETL)

```
┌──────────────────────────────────────────────────────────────┐
│                    Apache Airflow DAG                        │
│              Schedule: 0 9 * * *  (daily, 09:00 AM)         │
└─────────────────────┬────────────────────────────────────────┘
                      │
             ┌────────▼────────┐
             │    EXTRACT       │
             │   Read .xlsx     │
             │   via Pandas     │
             └────────┬────────┘
                      │
             ┌────────▼────────┐
             │   TRANSFORM      │
             │  Date arithmetic │
             │  Week scan       │   ← Monday to Sunday (7-day window)
             │  Classify:       │
             │    missed /      │
             │    today /       │
             │    upcoming      │
             └────────┬────────┘
                      │
             ┌────────▼────────┐
             │     LOAD         │
             │  Telegram Bot    │
             │  API — push      │
             │  notification    │
             └────────┬────────┘
                      │
             ┌────────▼────────┐
             │   Task 2         │
             │  Random Quote    │   ← ZenQuotes API call
             │  → Airflow log   │
             └─────────────────┘

Task dependency:  check_birthdays  ──►  print_random_quote
```

---

## Technical Implementation

### Stack

| Layer | Technology | Why This Choice |
|---|---|---|
| Orchestration | Apache Airflow | Industry-standard pipeline scheduler — used at Airbnb, Grab, Gojek, LinkedIn |
| Language | Python 3.8+ | Native Airflow language; dominant in data engineering |
| Data Ingestion | Pandas `read_excel` | Handles `.xlsx` natively; optimized for tabular data |
| Scheduling | Cron via Airflow | Fine-grained time control, decoupled from application logic |
| Notification | Telegram Bot API (REST) | Push notification to any device in under 2 seconds |
| Runtime | Linux / WSL2 | Production-equivalent environment for local pipeline development |

---

### Extract — Reading Structured Data

```python
base_dir  = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(base_dir, 'birthday_data.xlsx')
df = pd.read_excel(file_path)
```

The file path is **dynamically resolved** relative to the DAG file — no hardcoded absolute paths. The pipeline runs identically on any machine that clones the repository.

---

### Transform — Analytical Logic

The pipeline does not simply ask "is today someone's birthday?" That is reactive and narrow.

Instead it scans the **entire current week (Monday through Sunday)** — a temporal window analysis:

```python
start_of_week = today - timedelta(days=today.weekday())

for i in range(7):
    current_day = start_of_week + timedelta(days=i)
    matched = df[df['date'].apply(
        lambda x: (x.month, x.day) == (current_day.month, current_day.day)
    )]
```

Each matched birthday is then **classified into one of three analytical states**:

| State | Condition | Notification Sent |
|---|---|---|
| `missed` | `current_day < today` | "🎂 X's birthday was missed on Monday!" |
| `today` | `current_day == today` | "🎉 Happy Birthday, X! Today is your special day!" |
| `upcoming` | `current_day > today` | "🎈 Upcoming — X's birthday is on Friday!" |

This classification is the core analytical output — turning raw date records into contextual, actionable insights.

---

### Load — Delivering the Output

Each classified message is pushed to Telegram via REST:

```python
url    = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
params = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
response = requests.get(url, params=params, timeout=15)
```

Credentials are loaded from a `.env` file — never embedded in source code.

---

## Engineering Decisions

**Why Apache Airflow instead of a plain cron job?**

A bare cron job runs and disappears — no visibility, no audit trail, no observability. Airflow adds:

- Web UI showing every run's success/failure status
- Full task-level log storage and retrieval
- Explicit task dependency management
- Pause and resume without editing system cron
- DAG versioning and reusability across teams

This is the difference between a script and a **production-grade data pipeline**.

---

**Why scan the full week instead of only today?**

Same-day checks are reactive. A week-scope scan is proactive: you see that someone's birthday was yesterday (missed — still time for a belated message) and someone else's is in four days (upcoming — time to prepare). This is a deliberate analytical design choice — it turns a point-in-time lookup into a **temporal window analysis**.

---

**Why Telegram over email?**

Email carries high friction — inbox noise, delayed opens, easy to miss. Telegram delivers a push notification to your phone in under 2 seconds. For a time-sensitive alerting system, delivery latency and open rate are critical metrics. Telegram wins both.

---

**Why ZenQuotes API over a hardcoded quote?**

The `print_random_quote` task demonstrates a second pattern: calling an external API for enrichment. It also shows **graceful degradation** — if the API is unreachable, the pipeline selects from a local fallback list and continues without failure. This mirrors how production pipelines handle optional data sources.

---

## Observability & Error Handling

A pipeline that fails silently is worse than no pipeline at all.

Every step in the pipeline emits structured log output:

```python
print(f"[EXTRACT] Source file : {file_path}")
print(f"[EXTRACT] Loaded {len(df)} records")
print(f"[TRANSFORM] Scanning {day_name} ({current_day.strftime('%m-%d')})")
print(f"[LOAD] HTTP {response.status_code}")
```

These logs are captured by Airflow and stored per-task, per-run — inspectable at any time in the Airflow Web UI.

**Graceful failure with user-facing error reporting:**

```python
except Exception as e:
    traceback.print_exc()
    send_telegram_message(f"⚠️ Birthday pipeline error: {e}")
```

If the pipeline breaks — missing file, API timeout, malformed data — the error is caught and **pushed to Telegram immediately**. The engineer is informed without having to check the Airflow UI. This is the observability pattern used in production data systems.

---

## Testing Strategy

The pipeline ships with a **standalone test script** (`tests/test_birthday.py`) that validates core logic independently of Airflow.

**Why this matters:**

- Runs the full ETL chain without starting any Airflow service
- Faster iteration loop on transformation logic
- Validates Telegram API integration before DAG deployment
- Mirrors the separation of concerns used in professional data engineering: **test the logic, then orchestrate it**

```bash
python3 tests/test_birthday.py
```

---

## Results

| Metric | Before | After |
|---|---|---|
| Birthdays missed per month | 2–4 | **0** |
| Daily time spent on reminders | ~5 min | **0 min** |
| Advance notice on upcoming birthdays | 0 days (same day only) | **Up to 6 days ahead** |
| Failure visibility | Silent — no notification | **Error pushed to Telegram instantly** |
| Run auditability | None | **Full logs stored per-run in Airflow UI** |
| Scalability | 1 person's effort per entry | **Unlimited — add a row, get a reminder forever** |

---

## Skills Demonstrated

### Data Engineering

- Designed and deployed a complete ETL pipeline on Apache Airflow (industry-standard orchestrator)
- Defined multi-task DAG with explicit dependency chain: `check_birthdays >> print_random_quote`
- Applied `catchup=False` to prevent backfill accumulation on scheduler restart
- Implemented production-level structured logging throughout every pipeline layer
- Separated orchestration from business logic for maintainability and testability

### Data Analysis

- Translated a business question into structured analytical logic with classified outputs
- Designed a temporal window analysis (Monday–Sunday scan) for proactive vs. reactive insight delivery
- Implemented three-state classification (`missed` / `today` / `upcoming`) for contextual interpretation
- Delivered analysis results as actionable, human-readable notifications — not raw data dumps

### Python & Software Engineering

- File I/O with dynamic path resolution (portable across environments)
- Date arithmetic using `datetime` and `timedelta`
- DataFrame filtering using Pandas with lambda expressions
- REST API integration with response validation and timeout handling
- Clean exception handling with user-facing error reporting
- Standalone test script decoupled from orchestration infrastructure

### Production & DevOps Mindset

- Credential management via environment variables (zero secrets in source code)
- Cron scheduling decoupled from application code
- Graceful failure with self-reporting error messages pushed to the notification channel
- Graceful API degradation — fallback list when external quote API is unavailable
- Pipeline deployed and tested on Linux/WSL2 — matching production-grade environments

---

## What I Would Build Next

| Enhancement | Why It Matters |
|---|---|
| **PostgreSQL or BigQuery backend** | Replace Excel with a proper database for concurrent writes, query performance, and scalability to thousands of records |
| **dbt transformation layer** | Version-controlled, testable SQL models for the birthday classification logic |
| **Monitoring dashboard (Grafana / Metabase)** | Visualise pipeline run history, failure rates, and notification delivery trends |
| **Multi-channel delivery** | Route notifications to Slack, WhatsApp, or email based on user preference |
| **Parameterized DAG runs** | Accept timezone per person — a step toward true multi-tenant pipeline design |
| **Data quality checks** | Validate incoming data (null dates, duplicate names) before processing |

---

## Portfolio Screenshots — What to Capture

These are the screenshots that make this portfolio compelling to a hiring manager. Each one proves a specific capability.

---

### Screenshot 1 — Airflow Graph View: All Tasks Green

**Where:** Airflow UI → click `birthday_reminder` DAG → **Graph** tab → after a successful run

**What it shows:**
- Complete pipeline executed successfully end-to-end
- Two tasks in correct dependency order (`check_birthdays` → `print_random_quote`)
- Proficiency with the industry-standard orchestration tool
- Green = success — the most universally understood signal in data engineering

**Caption:** *"Airflow Graph View — both tasks completed successfully in the correct dependency order."*

> **This is the single most important screenshot for a data engineering hiring manager.**

---

### Screenshot 2 — Telegram Receiving the Notification

**Where:** Telegram app — the chat with your bot

**What it shows:**
- The pipeline works end-to-end in the real world — not just on paper
- Data was read, classified, and delivered to a live system
- Most human and emotionally resonant screenshot in the portfolio

**Caption:** *"Automated birthday notification delivered to Telegram — triggered by Airflow DAG, zero manual action."*

---

### Screenshot 3 — Airflow Task Logs

**Where:** Airflow UI → `birthday_reminder` DAG → any run → `check_birthdays` task → **Log** tab

**What it shows:**
- Every pipeline step is observable and traceable
- Coding with logging in mind — a mark of production-minded engineers
- Full data flow: file path → rows loaded → days scanned → messages sent

**Caption:** *"Full task logs in Airflow — data ingestion, birthday classification, and Telegram API call. Every step is observable."*

---

### Screenshot 4 — Airflow DAGs List

**Where:** Airflow UI → DAGs list page

**What it shows:**
- DAG is registered, active, and scheduled
- Cron expression visible in the Schedule column
- Next Run timestamp visible — proves automation is live

**Caption:** *"Birthday DAG active in Airflow with daily 09:00 schedule — fully automated."*

---

### Screenshot 5 — Terminal: Standalone Test

**Where:** Terminal after running `python3 tests/test_birthday.py`

**What it shows:**
- Test script validates logic independently of Airflow
- Full output: file read → rows loaded → messages classified → Telegram delivered
- Testing discipline before orchestration

**Caption:** *"Standalone test script — full ETL logic from Excel ingestion to Telegram delivery, independent of Airflow."*

---

### Screenshot Priority

| Priority | Screenshot | What It Proves |
|---|---|---|
| **#1 — Must have** | Graph View — all tasks green | Pipeline execution, Airflow proficiency |
| **#2 — Must have** | Telegram receiving the message | End-to-end working system |
| **#3 — Must have** | Task logs showing full trace | Observability and logging mindset |
| **#4 — Strong** | DAGs list with schedule & next run | Scheduling and automation config |
| **#5 — Good** | Terminal: test script output | Testing mindset, standalone validation |
