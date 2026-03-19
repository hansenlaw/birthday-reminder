#!/usr/bin/env python3
"""
Standalone test script for the Birthday Reminder pipeline.

Runs the full ETL logic (Extract → Transform → Load) independently of
Airflow — no scheduler, no webserver, no DAG context required.

Usage:
    # Test with today's actual date:
    python3 tests/test_birthday.py

    # Test with a specific date (useful when no one has a birthday today):
    python3 tests/test_birthday.py --date 2026-09-17

Run from the project root:
    cd ~/birthday-reminder
    python3 tests/test_birthday.py
"""

import sys
import os
import time
import socket
import argparse
from datetime import datetime, timedelta

# ── Path setup ───────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAGS_DIR     = os.path.join(PROJECT_ROOT, 'dags')
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, DAGS_DIR)


# ── Load .env credentials ────────────────────────────────────────────────────
def _load_env_file():
    env_path = os.path.join(PROJECT_ROOT, '.env')
    if not os.path.exists(env_path):
        print("INFO: .env file not found — relying on shell environment variables.")
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip())
    print("INFO: .env loaded successfully.")

_load_env_file()


# ── Core imports ──────────────────────────────────────────────────────────────
import pandas as pd
import requests
import urllib3
import random

TELEGRAM_TOKEN   = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
TELEGRAM_HOST    = 'api.telegram.org'

FALLBACK_QUOTES = [
    "Every day is a new opportunity to make a difference.",
    "Data is the new oil, but insight is the new gold.",
    "Without data, you're just another person with an opinion.",
    "The goal is to turn data into information, and information into insight.",
    "In God we trust; all others must bring data.",
]


# ── Telegram helper ───────────────────────────────────────────────────────────

def _post_telegram(token, chat_id, text, via_ip=False):
    """
    Low-level Telegram POST.
    via_ip=True → resolve hostname → IP, add Host header, skip cert verification.
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
    Push a message to Telegram with automatic SSL fallback.
    Tries standard HTTPS first; if blocked (SNI filtering), retries via
    direct-IP connection which bypasses hostname-based filtering.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("WARNING: Telegram credentials not set — message not sent.")
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


# ── ETL logic ─────────────────────────────────────────────────────────────────

def check_birthdays(override_date=None):
    """
    ETL pipeline:
      Extract   — read birthday_data.xlsx
      Transform — scan Monday-to-Sunday window; classify missed/today/upcoming
      Load      — push notifications to Telegram

    Args:
        override_date: datetime | None.  If set, treats this as "today" instead
                       of the actual current date. Useful for testing specific dates.
    """
    try:
        # ── Extract ───────────────────────────────────────────────────────────
        file_path = os.path.join(DAGS_DIR, 'birthday_data.xlsx')
        print(f"\n[EXTRACT] Source: {file_path}")
        df = pd.read_excel(file_path)
        print(f"[EXTRACT] Loaded {len(df)} records | columns: {df.columns.tolist()}")
        print(df.head())

        # ── Transform ─────────────────────────────────────────────────────────
        today         = override_date if override_date else datetime.now()
        start_of_week = today - timedelta(days=today.weekday())

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

        # ── Load ──────────────────────────────────────────────────────────────
        print(f"\n[LOAD] Dispatching {len(messages)} notification(s)")
        for msg in messages:
            send_telegram_message(msg)

    except Exception as e:
        import traceback
        print(f"\n[ERROR] check_birthdays failed: {e}")
        traceback.print_exc()
        send_telegram_message(f"⚠️ Birthday pipeline error: {e}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Birthday Reminder — standalone test runner'
    )
    parser.add_argument(
        '--date',
        type=str,
        default=None,
        metavar='YYYY-MM-DD',
        help='Override "today" with a specific date for testing (e.g. 2026-09-17)'
    )
    args = parser.parse_args()

    override = None
    if args.date:
        try:
            override = datetime.strptime(args.date, '%Y-%m-%d')
            print(f"INFO: Date override active → {override.strftime('%Y-%m-%d %A')}")
        except ValueError:
            print(f"ERROR: Invalid date format '{args.date}'. Use YYYY-MM-DD.")
            sys.exit(1)

    print("=" * 60)
    print("  Birthday Reminder — Standalone Test")
    print("=" * 60)
    check_birthdays(override_date=override)
    print("\n" + "=" * 60)
    print("  Test complete.")
    print("=" * 60)
