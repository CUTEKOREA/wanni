#!/usr/bin/env python3
"""Daily driver: pick today's 3 expressions, render cards, send to my KakaoTalk.

Cron fires early to absorb GitHub Actions delay; --wait HH:MM (UTC) sleeps
until the exact send time. Courses: th (08:00 KST), en (11:40 KST).
"""
import argparse
import csv
import os
import time
import urllib.parse
from datetime import date, datetime, timedelta, timezone

import kakao
import render

KST = timezone(timedelta(hours=9))
ROOT = os.path.dirname(os.path.abspath(__file__))

COURSE_META = {
    "th": dict(title="오늘의 태국어", sl="th", start_env="START_DATE"),
    "en": dict(title="오늘의 영어", sl="en", start_env="START_DATE_EN"),
}


def total_days(course):
    path = os.path.join(ROOT, "data", render.COURSES[course]["csv"])
    with open(path, encoding="utf-8") as f:
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


def tts_link(text, sl):
    return (f"https://translate.google.com/?sl={sl}&tl=ko&op=translate&text="
            + urllib.parse.quote(text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", default="th", choices=list(COURSE_META))
    ap.add_argument("--day", type=int, help="override day number")
    ap.add_argument("--wait", help="sleep until HH:MM UTC before sending")
    ap.add_argument("--dry-run", action="store_true", help="render only, no send")
    a = ap.parse_args()
    meta = COURSE_META[a.course]

    kst = today_kst()
    start = date.fromisoformat(os.environ.get(meta["start_env"], str(kst)))
    day = a.day or (kst - start).days % total_days(a.course) + 1
    weekday = kst.weekday()

    rows, paths = render.render_day(day, weekday, os.path.join(ROOT, "out"), a.course)
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
                    title=f'{meta["title"]} {i}/{len(rows)} · DAY {day:03d}',
                    desc=f'{row["ko"]}\n{row["text"]} [{row["pron"]}]',
                    content_link=url,  # tap card -> open full image (zoomable)
                    button_link=tts_link(row["text"], meta["sl"]))
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(5)
        print(f"sent {i}/{len(rows)}")
        time.sleep(2)


if __name__ == "__main__":
    main()
