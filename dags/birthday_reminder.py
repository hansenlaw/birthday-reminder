"""
Birthday Reminder Pipeline
==========================
Automated ETL pipeline that scans birthday records for the current week,
classifies each birthday by temporal proximity (missed / today / upcoming),
and delivers personalised notifications to Telegram via the Bot API.

DAG ID  : birthday_reminder
Schedule: daily at 09:00 AM  (cron: 0 9 * * *)
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timezone, timedelta
import pandas as pd
import requests
import urllib3
import random
import socket
import time
import os


# ---------------------------------------------------------------------------
# Environment — load .env from the project root automatically
# ---------------------------------------------------------------------------
def _load_env_file():
    """Read KEY=VALUE pairs from .env and inject into os.environ (no overwrite)."""
    env_path = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    )
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip())

_load_env_file()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TELEGRAM_TOKEN   = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
TELEGRAM_HOST    = 'api.telegram.org'

FALLBACK_QUOTES = [
    "Every day is a new opportunity to make a difference.",
    "Data is the new oil, but insight is the new gold.",
    "Without data, you're just another person with an opinion.",
    "The goal is to turn data into information, and information into insight.",
    "In God we trust; all others must bring data.",
    "Not everything that counts can be counted, and not everything that can be counted counts.",
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _post_telegram(token, chat_id, text, via_ip=False):
    """
    Low-level Telegram POST.
    via_ip=True  → resolve hostname to IP, set Host header, skip cert verification.
                   Workaround for ISP-level SNI-based blocking of api.telegram.org.
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    if via_ip:
        ip  = socket.gethostbyname(TELEGRAM_HOST)
        url = f'https://{ip}/bot{token}/sendMessage'
        headers = {'Host': TELEGRAM_HOST}
        verify  = False
        print(f"[LOAD] Using IP fallback → {ip}")
    else:
        url     = f'https://{TELEGRAM_HOST}/bot{token}/sendMessage'
        headers = {}
        verify  = True

    return requests.post(
        url,
        data={'chat_id': chat_id, 'text': text},
        headers=headers,
        verify=verify,
        timeout=20,
    )


def send_telegram_message(message, retries=3, backoff=2):
    """
    Push a text message to Telegram.
    Tries standard HTTPS first; if blocked by SNI filtering, falls back to
    direct-IP connection (resolve → IP, Host header, verify=False).
    Retries up to `retries` times per strategy with exponential backoff.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("WARNING: Telegram credentials not configured — message skipped.")
        print(f"  Content: {message}")
        return False

    for strategy_name, via_ip in [("standard HTTPS", False), ("IP fallback", True)]:
        print(f"[LOAD] Strategy: {strategy_name}")
        for attempt in range(1, retries + 1):
            try:
                print(f"[LOAD] Attempt {attempt}/{retries} — chat {TELEGRAM_CHAT_ID}")
                response = _post_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, message, via_ip=via_ip)
                print(f"[LOAD] HTTP {response.status_code}")
                if response.status_code == 200:
                    print("[LOAD] ✅ Message delivered successfully.")
                    return True
                else:
                    print(f"[LOAD] API error: {response.text}")
            except Exception as e:
                print(f"[LOAD] Attempt {attempt} failed: {e}")

            if attempt < retries:
                wait = backoff ** attempt
                print(f"[LOAD] Retrying in {wait}s …")
                time.sleep(wait)

    print("[LOAD] ❌ All delivery strategies exhausted — message not sent.")
    return False


# ---------------------------------------------------------------------------
# Task 1 — check_birthdays  (Extract → Transform → Load)
# ---------------------------------------------------------------------------
def check_birthdays():
    """
    Full ETL task:
      Extract   — read birthday_data.xlsx with Pandas
      Transform — scan the Monday-to-Sunday window of the current week;
                  classify each match as 'missed', 'today', or 'upcoming'
      Load      — push classified notifications to Telegram
    """
    try:
        # ── Extract ──────────────────────────────────────────────────────────
        base_dir  = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, 'birthday_data.xlsx')
        print(f"[EXTRACT] Source file : {file_path}")

        df = pd.read_excel(file_path)
        print(f"[EXTRACT] Loaded {len(df)} records | columns: {df.columns.tolist()}")
        print(df.head())

        # ── Transform ────────────────────────────────────────────────────────
        today         = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())  # Monday

        print(f"\n[TRANSFORM] Today      : {today.strftime('%Y-%m-%d %A')}")
        print(f"[TRANSFORM] Week start : {start_of_week.strftime('%Y-%m-%d %A')}")
        print(f"[TRANSFORM] Week end   : {(start_of_week + timedelta(days=6)).strftime('%Y-%m-%d %A')}")

        messages       = []
        birthday_found = False

        for i in range(7):
            current_day = start_of_week + timedelta(days=i)
            day_name    = current_day.strftime('%A')
            month_day   = (current_day.month, current_day.day)
            print(f"\n[TRANSFORM] Scanning {day_name} ({current_day.strftime('%m-%d')})")

            matched = df[df['date'].apply(lambda x: (x.month, x.day) == month_day)]
            print(f"[TRANSFORM] Matches  : {len(matched)}")

            for name in matched['name']:
                birthday_found = True
                if current_day.date() < today.date():
                    msg = f"🎂 {name}'s birthday was missed on {day_name}!"
                elif current_day.date() == today.date():
                    msg = f"🎉 Happy Birthday, {name}! Today is your special day!"
                else:
                    msg = f"🎈 Upcoming — {name}'s birthday is on {day_name}!"
                print(f"[TRANSFORM] → {msg}")
                messages.append(msg)

        if not birthday_found:
            msg = "📅 No birthdays this week. See you next Monday!"
            messages.append(msg)
            print(f"[TRANSFORM] {msg}")

        # ── Load ─────────────────────────────────────────────────────────────
        print(f"\n[LOAD] Dispatching {len(messages)} notification(s)")
        for msg in messages:
            send_telegram_message(msg)

    except Exception as e:
        import traceback
        print(f"[ERROR] check_birthdays failed: {e}")
        traceback.print_exc()
        send_telegram_message(f"⚠️ Birthday pipeline error: {e}")


# ---------------------------------------------------------------------------
# Task 2 — print_random_quote
# ---------------------------------------------------------------------------
def print_random_quote():
    """Fetch a motivational quote from ZenQuotes API; fallback to local list."""
    try:
        response = requests.get('https://zenquotes.io/api/random', timeout=10)
        if response.status_code == 200:
            data   = response.json()[0]
            quote  = data.get('q', '').strip()
            author = data.get('a', '').strip()
            print(f'Quote of the day: "{quote}" — {author}')
            return
        print(f"ZenQuotes API returned HTTP {response.status_code}, using fallback.")
    except Exception as e:
        print(f"Could not reach ZenQuotes API: {e} — using fallback.")

    print(f'Quote of the day: "{random.choice(FALLBACK_QUOTES)}"')


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------
default_args = {
    'start_date':       datetime(2024, 1, 1, tzinfo=timezone.utc),
    'email_on_failure': False,
    'email_on_retry':   False,
    'retries':          0,
}

with DAG(
    dag_id='birthday_reminder',
    default_args=default_args,
    description='Daily birthday notification pipeline — Excel → Classify → Telegram',
    schedule_interval='0 9 * * *',  # Every day at 09:00 AM  (min hour day month dow)
    catchup=False,
    tags=['notifications', 'etl', 'portfolio'],
) as dag:

    check_birthdays_task = PythonOperator(
        task_id='check_birthdays',
        python_callable=check_birthdays,
    )

    print_random_quote_task = PythonOperator(
        task_id='print_random_quote',
        python_callable=print_random_quote,
    )

    check_birthdays_task >> print_random_quote_task
