#!/usr/bin/env python3
"""Render daily expression cards (1080x1350 PNG) via headless Chrome.

Chrome is used instead of Pillow because Thai combining marks (tone marks,
above/below vowels) need complex-script shaping that Pillow lacks without
libraqm. Chrome ships preinstalled on GitHub ubuntu runners and macOS.
No SQL anywhere; template values are html-escaped local CSV fields.
"""
import csv
import html
import os
import shutil
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))

# Thai traditional day-of-week colors, Mon..Sun
DAY_COLORS = ["#D9A800", "#D6437C", "#2E8B3E", "#D96C13", "#3B6FC4", "#6E4396", "#C0392B"]
DAY_NAMES = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]

COURSES = {
    "th": dict(csv="expressions.csv", prefix="", label="완니",
               main_font="NSTH, NSKR, sans-serif", main_size=120,
               band=["#B5313E", "#F4F1E8", "#2E3A87", "#F4F1E8", "#B5313E"],
               brand="<b>วันนี้</b> · 매일 아침 8시"),
    "en": dict(csv="expressions_en.csv", prefix="en_", label="완니 EN",
               main_font="NSKR, sans-serif", main_size=86,
               band=["#3C3B6E", "#FFFFFF", "#B22234", "#FFFFFF", "#3C3B6E"],
               brand="<b>Today</b> · 매일 오전 11:40"),
    "zh": dict(csv="expressions_zh.csv", prefix="zh_", label="완니 ZH",
               main_font="NSSC, NSKR, sans-serif", main_size=110,
               band=["#DE2910", "#FFDE00", "#DE2910", "#FFDE00", "#DE2910"],
               brand="<b>今天</b> · 매일 오후 5:30"),
}
BAND_FLEX = [1, 1, 2, 1, 1]

CARD_TMPL = """<!doctype html>
<meta charset="utf-8">
<style>
@font-face {{ font-family: NSKR; src: url("{root}/fonts/NotoSansKR.ttf"); font-weight: 100 900; }}
@font-face {{ font-family: NSTH; src: url("{root}/fonts/NotoSansThai.ttf"); font-weight: 100 900; }}
@font-face {{ font-family: NSSC; src: url("{root}/fonts/NotoSansSC.ttf"); font-weight: 100 900; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: 1080px; height: 1350px; background: #FFFDF6; overflow: hidden;
  font-family: NSKR, NSSC, sans-serif; color: #241F14; }}
.band {{ height: 36px; display: flex; flex-direction: column; }}
.band i {{ display: block; }}
.page {{ padding: 56px 80px 0; position: relative; height: 1314px; }}
.head {{ display: flex; justify-content: space-between; align-items: baseline; }}
.head .l {{ font-size: 30px; font-weight: 500; letter-spacing: .34em; color: #8A8371; }}
.head .r {{ font-size: 31px; font-weight: 700; color: {accent}; }}
.ko {{ margin-top: 56px; font-size: 70px; font-weight: 700; line-height: 1.35; }}
.main {{ margin-top: 22px; font-family: {main_font}; font-size: {main_size}px;
  font-weight: 700; line-height: 1.3; color: #2E3A87; }}
.pron {{ margin-top: 18px; font-size: 55px; font-weight: 500; color: #6B6455; }}
.pron b {{ color: {accent}; font-weight: 700; }}
.div {{ margin-top: 38px; border-top: 3px dashed #E2DBC8; }}
.vocab {{ margin-top: 36px; }}
.vocab .row {{ display: flex; align-items: baseline; gap: 26px; margin-bottom: 22px; }}
.vocab .tw {{ font-family: NSTH, NSSC, NSKR, sans-serif; font-size: 55px; font-weight: 600; }}
.vocab .m {{ font-size: 46px; color: #4C4636; }}
.vocab .note {{ font-size: 38px; color: #8A8371; margin: -8px 0 22px; }}
.foot {{ position: absolute; left: 80px; right: 80px; bottom: 58px;
  display: flex; justify-content: space-between; align-items: center; }}
.foot .cat {{ font-size: 28px; font-weight: 700; color: {accent};
  border: 2.5px solid {accent}; border-radius: 999px; padding: 8px 26px; }}
.foot .brand {{ font-size: 28px; color: #8A8371; }}
.foot .brand b {{ font-family: NSTH, NSSC, NSKR, sans-serif; font-weight: 600; }}
</style>
<div class="band">{band}</div>
<div class="page">
  <div class="head"><span class="l">{label} · DAY {day:03d}</span><span class="r">{weekday} {slot}/{total}</span></div>
  <div class="ko">{ko}</div>
  <div class="main">{main}</div>
  <div class="pron"><b>[</b>{pron}<b>]</b></div>
  <div class="div"></div>
  <div class="vocab">{vocab}</div>
  <div class="foot"><span class="cat">{category}</span><span class="brand">{brand}</span></div>
</div>
"""


def chrome_bin():
    for c in [os.environ.get("CHROME_BIN"), "google-chrome", "chromium-browser", "chromium",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]:
        if c and (shutil.which(c) or os.path.exists(c)):
            return c
    raise SystemExit("Chrome/Chromium not found; set CHROME_BIN")


def vocab_html(spec):
    out = []
    for item in spec.split(";"):
        parts = item.split(":", 2)
        if len(parts) != 3:
            continue
        word, pron, meaning = (html.escape(p) for p in parts)
        note = ""
        if "|" in meaning:
            meaning, note = meaning.split("|", 1)
        out.append(f'<div class="row"><span class="tw">{word}</span>'
                   f'<span class="m">{pron} · {meaning}</span></div>')
        if note:
            out.append(f'<div class="note">· {note}</div>')
    return "\n".join(out)


def render_card(row, slot_no, total, weekday_idx, out_path, course="th"):
    cfg = COURSES[course]
    band = "".join(f'<i style="flex:{fl};background:{c}"></i>'
                   for fl, c in zip(BAND_FLEX, cfg["band"]))
    page = CARD_TMPL.format(
        root=ROOT, accent=DAY_COLORS[weekday_idx], day=int(row["day"]),
        weekday=DAY_NAMES[weekday_idx], slot=slot_no, total=total,
        label=cfg["label"], band=band, brand=cfg["brand"],
        main_font=cfg["main_font"], main_size=cfg["main_size"],
        ko=html.escape(row["ko"]), main=html.escape(row["text"]),
        pron=html.escape(row["pron"]), vocab=vocab_html(row["vocab"]),
        category=html.escape(row["category"]),
    )
    with tempfile.NamedTemporaryFile("w", suffix=".html", dir=ROOT, delete=False,
                                     encoding="utf-8") as f:
        f.write(page)
        tmp = f.name
    try:
        subprocess.run(
            [chrome_bin(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--force-device-scale-factor=1", "--window-size=1080,1350",
             f"--screenshot={out_path}", f"file://{tmp}"],
            check=True, capture_output=True, timeout=60)
    finally:
        os.unlink(tmp)
    return out_path


def load_day(day, course="th"):
    path = os.path.join(ROOT, "data", COURSES[course]["csv"])
    with open(path, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if int(r["day"]) == day]
    rows.sort(key=lambda r: int(r["slot"]))
    if not rows:
        raise SystemExit(f"no rows for day {day} in {path}")
    return rows


def render_day(day, weekday_idx, out_dir, course="th"):
    os.makedirs(out_dir, exist_ok=True)
    rows = load_day(day, course)
    prefix = COURSES[course]["prefix"]
    paths = []
    for i, row in enumerate(rows, 1):
        p = os.path.join(out_dir, f"{prefix}day{day:03d}_{i}.png")
        render_card(row, i, len(rows), weekday_idx, p, course)
        paths.append(p)
    return rows, paths


if __name__ == "__main__":
    import argparse
    from datetime import date

    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=int, required=True)
    ap.add_argument("--course", default="th", choices=list(COURSES))
    ap.add_argument("--weekday", type=int, default=date.today().weekday())
    ap.add_argument("--out", default=os.path.join(ROOT, "out"))
    a = ap.parse_args()
    _, paths = render_day(a.day, a.weekday, a.out, a.course)
    print("\n".join(paths))
