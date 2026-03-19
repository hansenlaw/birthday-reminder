# Testing Guide — Birthday Reminder Pipeline

Complete walkthrough from a fresh clone to a fully verified, automatically running pipeline.
Follow every step in order. Nothing will be skipped.

---

## What You Will End Up With

After completing this guide you will have:

- Airflow running locally, serving the Web UI at `http://localhost:8080`
- The `birthday_reminder` DAG visible, active, and scheduled at 09:00 AM daily
- A successful manual test run with both tasks green in the Graph View
- A Telegram message received in real-time from the pipeline
- A verified automatic scheduled run proving zero human intervention is needed

---

## Overview

| Step | What Happens |
|---|---|
| 1 | Install prerequisites |
| 2 | Clone and set up the repo |
| 3 | Configure Telegram credentials |
| 4 | Initialise Airflow |
| 5 | Start Scheduler + Web Server |
| Part A | Run standalone test (no Airflow) |
| Part B | Trigger via Airflow CLI |
| Part C | Trigger via Airflow Web UI |
| Part D | Verify automated scheduling |

---

## Step 1 — Install Prerequisites

### Check Python (3.8 or higher required)

```bash
python3 --version
# Should print: Python 3.8.x or higher
```

If Python is missing (Ubuntu / WSL2):

```bash
sudo apt update && sudo apt install python3 python3-pip -y
```

### Check pip

```bash
pip3 --version
```

---

## Step 2 — Clone and Set Up

### Clone the repository

```bash
git clone https://github.com/hansenlaw/birthday-reminder.git
cd birthday-reminder
```

### Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `apache-airflow` — pipeline orchestration engine
- `pandas` + `openpyxl` — Excel file reading
- `requests` — HTTP client for Telegram and quotes API

> Airflow installation takes several minutes. This is normal. Wait for the prompt to return.

### Set Airflow home to the project folder

```bash
export AIRFLOW_HOME=$(pwd)
```

> **This is critical.** Without it, Airflow will not find the `dags/` folder.
>
> To make this permanent (so you never need to re-run it):
> ```bash
> echo 'export AIRFLOW_HOME=~/birthday-reminder' >> ~/.bashrc
> source ~/.bashrc
> ```

---

## Step 3 — Configure Telegram Credentials

### Create your local .env file

```bash
cp .env.example .env
```

### Fill in your credentials

```bash
nano .env
```

Replace the placeholder values with your real credentials:

```
TELEGRAM_BOT_TOKEN=6990555670:AAFV_GDrxpgrnd7dSm...   ← your bot token
TELEGRAM_CHAT_ID=5304908862                             ← your chat ID
```

Save and close (`Ctrl+O` → `Enter` → `Ctrl+X` in nano).

> **Why is .env not on GitHub?**
> The `.gitignore` file excludes `.env` from version control. Your credentials are never pushed to GitHub. Only the safe template `.env.example` is committed.

### Verify the credentials loaded correctly

```bash
cat .env
# You should see your token and chat ID — not placeholder text
```

---

## Step 4 — Initialise Airflow

Run these commands **once** on first setup. You do not need to repeat them.

### Initialise the metadata database

```bash
airflow db init
```

Expected output ends with:

```
DB: sqlite:////home/YOUR_USER/birthday-reminder/airflow.db
[...]
Initialization done
```

### Create an admin user for the Web UI

```bash
airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com
```

Expected:

```
Admin user admin created
```

> Change `--username` and `--password` to anything you prefer. Remember them for the web login.

---

## Step 5 — Start Services

Open **two terminal windows** (or split your terminal into two panes).

### Terminal 1 — Scheduler

```bash
cd ~/birthday-reminder
export AIRFLOW_HOME=$(pwd)
airflow scheduler
```

The scheduler processes DAG files and triggers runs at the configured time. You will see continuous log output — leave this terminal running.

### Terminal 2 — Web Server

```bash
cd ~/birthday-reminder
export AIRFLOW_HOME=$(pwd)
airflow webserver --port 8080
```

Wait ~15 seconds, then open:

```
http://localhost:8080
```

Log in with the username and password you created in Step 4.

> **Portfolio Screenshot #1**
> Screenshot the Airflow Web UI login page or home page.
> Caption: *"Airflow running locally — pipeline management interface live."*

---

## Part A — Standalone Test (No Airflow Needed)

This validates that the full ETL logic works before involving any Airflow infrastructure.
Run this in a **third terminal** (or stop the webserver temporarily).

```bash
cd ~/birthday-reminder
python3 tests/test_birthday.py
```

### What you should see

```
INFO: .env loaded successfully.
============================================================
  Birthday Reminder — Standalone Test
============================================================

[EXTRACT] Source: /home/YOUR_USER/birthday-reminder/dags/birthday_data.xlsx
[EXTRACT] Loaded 75 records | columns: ['name', 'date']
         name       date
0        Abel 2001-12-08
...

[TRANSFORM] Today      : 2026-03-19 Thursday
[TRANSFORM] Week start : 2026-03-16 Monday
[TRANSFORM] Week end   : 2026-03-22 Sunday

[TRANSFORM] Scanning Monday (03-16)
[TRANSFORM] Matches  : 0
...
[TRANSFORM] Scanning Thursday (03-19)
[TRANSFORM] Matches  : 1
[TRANSFORM] → 🎉 Happy Birthday, Hansen! Today is your special day!

[LOAD] Dispatching 1 notification(s)
[LOAD] Attempt 1/3 — sending to chat 5304908862
[LOAD] HTTP 200
[LOAD] Message delivered successfully.

============================================================
  Test complete.
============================================================
```

If no birthday falls this week, you will see `📅 No birthdays this week. See you next Monday!` — this is also sent to Telegram.

> **Portfolio Screenshot #2**
> Screenshot the full terminal output of `python3 tests/test_birthday.py`.
> Make sure the `[LOAD] Message delivered successfully.` line is visible.

> **Portfolio Screenshot #3**
> Screenshot your Telegram chat showing the birthday notification message.
> This is the most visual proof of end-to-end automation working.

---

## Part B — Trigger via Airflow CLI

Both the scheduler and webserver must be running (from Step 5).
Run these in a **third terminal.**

### Verify the DAG is registered

```bash
airflow dags list
```

Look for `birthday_reminder` in the output:

```
dag_id              | filepath                | owner   | paused
====================|=========================|=========|=======
birthday_reminder   | birthday_reminder.py    | airflow | True
```

> `paused = True` is expected — new DAGs always start paused.

> **Portfolio Screenshot #4**
> Screenshot the `airflow dags list` output with `birthday_reminder` visible.

### Unpause the DAG

```bash
airflow dags unpause birthday_reminder
```

Expected:

```
Dag: birthday_reminder, paused: False
```

### Trigger the DAG manually

```bash
airflow dags trigger birthday_reminder
```

Expected:

```
Created <DagRun birthday_reminder @ 2026-03-19T...: manual__..., externally triggered: True>
```

### Monitor the run

```bash
airflow dags list-runs -d birthday_reminder
```

Wait a few seconds then re-run until you see `success`:

```
run_id                  | state   | execution_date | run_type
========================|=========|================|=========
manual__2026-03-19...   | success | 2026-03-19...  | manual
```

> **Portfolio Screenshot #5**
> Screenshot `airflow dags list-runs` showing `state = success`.

### Inspect task logs from CLI

```bash
# List tasks in the DAG
airflow tasks list birthday_reminder

# View logs for a task (replace RUN_ID with the actual run_id from above)
airflow tasks logs birthday_reminder check_birthdays RUN_ID
```

---

## Part C — Trigger via Airflow Web UI

Both services must be running. Open `http://localhost:8080` in your browser.

### Step C-1 — Open the DAGs page

Navigate to the DAGs list. Find `birthday_reminder`.

> **Portfolio Screenshot #6**
> Screenshot the DAGs list showing `birthday_reminder` with its schedule (`0 9 * * *`) and status toggle.

### Step C-2 — Ensure the DAG is active

If the toggle next to `birthday_reminder` is grey (paused), click it to turn it blue (active).

### Step C-3 — Trigger manually from the UI

Click the **▶ play button** on the right side of the `birthday_reminder` row → select **"Trigger DAG"** → confirm.

> **Portfolio Screenshot #7**
> Screenshot the DAG run page immediately after triggering — shows the new run appearing.

### Step C-4 — Watch the Graph View

Click on `birthday_reminder` → click the **Graph** tab.

Task boxes change colour as the pipeline executes:

| Colour | Status |
|---|---|
| Grey | Queued |
| Yellow | Running |
| Dark green | Success ✅ |
| Red | Failed ❌ |

> **Portfolio Screenshot #8 — Most Important**
> Screenshot the Graph View with **both tasks showing dark green (success)**.
> This is the strongest portfolio screenshot — it proves a complete successful pipeline run.

### Step C-5 — View task logs in the UI

Click the green `check_birthdays` box → click **Log**.

You should see structured log output including:

```
[EXTRACT] Source file : .../birthday_data.xlsx
[EXTRACT] Loaded 75 records
[TRANSFORM] Scanning Thursday (03-19)
[TRANSFORM] Matches  : 1
[TRANSFORM] → 🎉 Happy Birthday ...
[LOAD] HTTP 200
[LOAD] Message delivered successfully.
```

> **Portfolio Screenshot #9**
> Screenshot the full task log.
> Caption: *"Airflow captures every log line per task per run — full observability."*

---

## Part D — Verify Automated Scheduling

The DAG is configured to run **automatically every day at 09:00 AM** via cron `0 9 * * *`.

> **Important:** The scheduler must be running continuously for automatic runs to trigger. If you stop the scheduler, automatic runs will not happen.

### Check the next scheduled run in the Web UI

In the DAGs list, the `birthday_reminder` row shows:

- **Schedule** column: `0 9 * * *`
- **Next Run** column: exact timestamp of the next automatic execution

> **Portfolio Screenshot #10**
> Screenshot the DAGs list showing both the **Schedule** and **Next Run** columns.
> Caption: *"Daily 09:00 AM schedule active — pipeline runs automatically without any manual action."*

### Confirm a scheduled run happened (wait until 09:00 AM)

```bash
airflow dags list-runs -d birthday_reminder
```

Automated runs show `scheduled` in the `run_type` column:

```
run_id                      | state   | run_type
============================|=========|=========
scheduled__2026-03-20...    | success | scheduled   ← automated run
manual__2026-03-19...       | success | manual      ← your manual trigger
```

> **Portfolio Screenshot #11**
> Screenshot showing a run with `run_type = scheduled` and `state = success`.
> This is definitive proof that the pipeline runs automatically without human intervention.

---

## Screenshot Checklist

| # | What to Screenshot | Priority | What It Proves |
|---|---|---|---|
| 1 | Airflow Web UI login / home | Good | Live environment running |
| 2 | Terminal: `test_birthday.py` full output | Strong | Standalone ETL logic correct |
| **3** | **Telegram: birthday message received** | **Must have** | **Real end-to-end delivery** |
| 4 | `airflow dags list` with `birthday_reminder` | Good | DAG registered and recognised |
| 5 | `list-runs` showing `success` state | Strong | CLI run monitoring |
| 6 | DAGs page with schedule column | Strong | Scheduling configured |
| 7 | DAG run page after trigger | Good | Pipeline triggered from UI |
| **8** | **Graph View — both tasks dark green** | **Must have** | **Full pipeline success proof** |
| **9** | **Task log — full structured trace** | **Must have** | **Observability mindset** |
| 10 | DAGs list with Next Run timestamp | Strong | Scheduler active |
| **11** | **`list-runs` with `run_type = scheduled`** | **Must have** | **True automation proven** |

---

## Quick Reference — All Commands

```bash
# ── Environment (run every new terminal) ─────────────────────────────────
export AIRFLOW_HOME=~/birthday-reminder

# ── One-time initialisation ───────────────────────────────────────────────
airflow db init
airflow users create --username admin --password admin \
    --firstname Admin --lastname User --role Admin \
    --email admin@example.com

# ── Start services (keep running) ─────────────────────────────────────────
airflow scheduler                        # Terminal 1
airflow webserver --port 8080            # Terminal 2

# ── Standalone test (no Airflow needed) ───────────────────────────────────
python3 tests/test_birthday.py

# ── DAG management ────────────────────────────────────────────────────────
airflow dags list                              # List all registered DAGs
airflow dags unpause birthday_reminder         # Enable auto-run
airflow dags pause   birthday_reminder         # Disable auto-run
airflow dags trigger birthday_reminder         # Trigger manually right now
airflow dags list-runs -d birthday_reminder    # View run history

# ── Task inspection ───────────────────────────────────────────────────────
airflow tasks list birthday_reminder
airflow tasks logs birthday_reminder check_birthdays RUN_ID

# ── Test a single task directly (no full DAG run) ─────────────────────────
airflow tasks test birthday_reminder check_birthdays 2024-01-01
```

---

## Troubleshooting

### DAG not showing in the UI or CLI

**Cause:** Syntax error in the DAG file, or scheduler hasn't picked it up yet.

```bash
# Check for syntax errors
python3 dags/birthday_reminder.py
# No output = file is valid

# Force the scheduler to reparse
airflow dags reserialize
```

Then wait 15–30 seconds and refresh the UI.

---

### Telegram message not arriving

**Step 1 — Verify credentials are loaded:**
```bash
python3 -c "
import os
def load_env():
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                k, _, v = line.partition('=')
                os.environ.setdefault(k, v)
load_env()
print('Token set:', bool(os.getenv('TELEGRAM_BOT_TOKEN')))
print('Chat ID set:', bool(os.getenv('TELEGRAM_CHAT_ID')))
"
```

**Step 2 — Test bot directly with curl:**
```bash
source <(cat .env | sed 's/^/export /')
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"
```

If this returns your bot's JSON info, the token is valid.

**Step 3 — Test message delivery:**
```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage?chat_id=${TELEGRAM_CHAT_ID}&text=hello+from+pipeline"
```

> If Telegram is unreachable (SSL/TLS error), this is a **network/firewall issue**, not a code bug.
> This can happen in WSL2 on certain networks. Try on a different network or use a VPN.
> The code handles delivery failures gracefully with retry logic — it will not crash.

---

### `AIRFLOW_HOME` not set

**Symptom:** Airflow cannot find the `birthday_reminder` DAG.

```bash
echo $AIRFLOW_HOME
# Should print: /home/YOUR_USER/birthday-reminder
```

If empty, re-set it:
```bash
export AIRFLOW_HOME=~/birthday-reminder
```

---

### Port 8080 already in use

```bash
lsof -i :8080   # Find what's using port 8080

# Use a different port
airflow webserver --port 8081
# Then open: http://localhost:8081
```

---

### `ModuleNotFoundError: No module named 'pandas'`

```bash
pip install -r requirements.txt
```

---

### Task stuck in "running" or "queued" state

```bash
airflow dags clear birthday_reminder
```

Then trigger a fresh run.

---

## Project File Reference

```
birthday-reminder/
├── dags/
│   ├── birthday_reminder.py    ← Main Airflow DAG (pipeline definition)
│   └── birthday_data.xlsx      ← Birthday data source (75 records)
├── tests/
│   └── test_birthday.py        ← Standalone test (no Airflow needed)
├── .env                        ← Your credentials (gitignored — never pushed to GitHub)
├── .env.example                ← Credential template (safe to share)
├── .gitignore                  ← Excludes .env, logs, airflow.db, __pycache__
├── requirements.txt            ← Python dependencies
├── README.md                   ← Project overview and quick start
├── PORTFOLIO_notion.md         ← Full portfolio writeup (Notion-ready)
└── TESTING_GUIDE.md            ← This file
```

---

## What to Read First (Recommended Order)

1. **`README.md`** — Start here. Understand what the project does and how to set it up.
2. **`TESTING_GUIDE.md`** — This file. Follow it step by step from top to bottom.
3. **`dags/birthday_reminder.py`** — Read the DAG code. It is fully commented with `[EXTRACT]`, `[TRANSFORM]`, `[LOAD]` labels.
4. **`tests/test_birthday.py`** — Read the standalone test. Same logic, no Airflow dependency.
5. **`PORTFOLIO_notion.md`** — Read the full technical writeup for deeper understanding of each design decision.
