#!/usr/bin/env python3
"""Pre-generate pronunciation MP3s for every expression (docs/audio/, served
via GitHub Pages). Run once per DB change: .venv/bin/python gen_audio.py"""
import asyncio
import csv
import os

import edge_tts

import render

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "docs", "audio")
VOICES = {
    "th": "th-TH-PremwadeeNeural",
    "en": "en-US-JennyNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
}


async def synth(sem, text, voice, path):
    async with sem:
        await edge_tts.Communicate(text, voice, rate="-10%").save(path)
        print(os.path.relpath(path, ROOT))


async def main():
    sem = asyncio.Semaphore(8)
    jobs = []
    for course, voice in VOICES.items():
        d = os.path.join(OUT, course)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(ROOT, "data", render.COURSES[course]["csv"]),
                  encoding="utf-8") as f:
            for row in csv.DictReader(f):
                path = os.path.join(d, f'd{int(row["day"]):02d}_{row["slot"]}.mp3')
                if not os.path.exists(path):
                    jobs.append(synth(sem, row["text"], voice, path))
    await asyncio.gather(*jobs)
    print(f"done: {len(jobs)} new files")


if __name__ == "__main__":
    asyncio.run(main())
