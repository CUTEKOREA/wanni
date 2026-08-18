#!/usr/bin/env python3
"""Daily driver: pick today's 3 expressions, render cards, send to my KakaoTalk.

Cron fires early (07:40 KST) to absorb GitHub Actions delay; --wait HH:MM (UTC)
sleeps until the exact send time (23:00 UTC = 08:00 KST).
"""
import argparse
import csv
import os
import time
import urllib.parse
from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

import kakao
import render

ROOT = os.path.dirname(os.path.abspath(__file__))


def total_days():
    with open(os.path.join(ROOT, "data", "expressions.csv"), encoding="utf-8") as f:
        return max(int(r["day"]) for r in csv.DictReader(f))


def today_kst():
    return datetime.now(KST).date()


def wait_until(hhmm_utc):
    h, m = map(int, hhmm_utc.split(":"))
    now = datetime.now(timezone.utc)
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    delta = (target - now).total_seconds()
    if delta > 0:
        print(f"waiting {int(delta)}s until {hhmm_utc} UTC")
        time.sleep(delta)


def tts_link(th):
    return ("https://translate.google.com/?sl=th&tl=ko&op=translate&text="
            + urllib.parse.quote(th))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=int, help="override day number")
    ap.add_argument("--wait", help="sleep until HH:MM UTC before sending")
    ap.add_argument("--dry-run", action="store_true", help="render only, no send")
    a = ap.parse_args()

    kst = today_kst()
    start = date.fromisoformat(os.environ.get("START_DATE", str(kst)))
    day = a.day or (kst - start).days % total_days() + 1
    weekday = kst.weekday()

    rows, paths = render.render_day(day, weekday, os.path.join(ROOT, "out"))
    print("rendered:", ", ".join(os.path.basename(p) for p in paths))
    if a.dry_run:
        return

    tok = kakao.refresh(kakao.load_tokens())
    if a.wait:
        wait_until(a.wait)

    for i, (row, path) in enumerate(zip(rows, paths), 1):
        url = kakao.upload_image(tok["access_token"], path)
        for attempt in (1, 2):
            try:
                kakao.send_feed(
                    tok["access_token"], url,
                    title=f"오늘의 태국어 {i}/{len(rows)} · DAY {day:03d}",
                    desc=f'{row["ko"]}\n{row["th"]} [{row["pron"]}]',
                    link_url=tts_link(row["th"]))
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(5)
        print(f"sent {i}/{len(rows)}")
        time.sleep(2)


if __name__ == "__main__":
    main()
