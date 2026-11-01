#!/usr/bin/env python3
"""Build per-platform post packs + a week queue for Buffer (no API key needed).

Reads carousels/*.json and out/<id>/slide1-4.png, then writes:
  out/<id>/instagram.txt   bilingual caption + hashtags (IG limit safe)
  out/<id>/facebook.txt    bilingual caption + a short hashtag set
  out/<id>/post.json       machine-readable pack
  schedule/week-YYYY-WW.json   five posts, one per workday, Doha time

Usage:  python3 make_pack.py [--week-of 2026-10-25] [--out schedule]
"""
import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from envload import load as load_env

HERE = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=3))  # Asia/Qatar, no DST
# Best-time slots for Doha (GCC research: lunch 11-13, evening 19-21), Mon..Sun
TIMES = {0: "12:30", 1: "19:30", 2: "12:30", 3: "19:30", 4: "12:30", 5: "12:30", 6: "12:30"}
CADENCE = 5
DIVIDER = "\n\n———\n\n"
IG_LIMIT = 2200
FB_LIMIT = 63206


def week_start(day):
    """Most recent/next Sunday on or after the Monday of that week."""
    return day - timedelta(days=(day.weekday() + 1) % 7)


def iso_week(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def bilingual(c):
    return c["caption_en"].strip() + DIVIDER + c["caption_ar"].strip()


def build(c):
    """Return (instagram_text, facebook_text) for one carousel."""
    body = bilingual(c) + "\n\n\U0001F4CD Doha, Qatar"
    ig_tags = " ".join(dict.fromkeys(c["hashtags_en"] + c["hashtags_ar"]))
    fb_tags = " ".join(dict.fromkeys(
        ["#RahisSheikhTrading", "#KitchenExhaust", "#Doha", "#CommercialKitchen", "#مطاعم_قطر"]
    ))
    ig = f"{body}\n\n{ig_tags}"
    fb = f"{body}\n\n{fb_tags}"
    if len(ig) > IG_LIMIT:
        raise SystemExit(f"{c['id']}: Instagram caption is {len(ig)} chars, max {IG_LIMIT}")
    if len(fb) > FB_LIMIT:
        raise SystemExit(f"{c['id']}: Facebook caption is {len(fb)} chars, max {FB_LIMIT}")
    return ig, fb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week-of", default=None, help="any date in the target week (default: next Sunday)")
    ap.add_argument("--out", default="schedule")
    ap.add_argument("--plan", default=None, help="JSON list of {id, due_at} for a custom order")
    ap.add_argument("--name", default=None, help="queue label (default: ISO week of the first post)")
    a = ap.parse_args()

    if a.week_of:
        start = week_start(date.fromisoformat(a.week_of))
    else:
        today = date.today()
        start = today + timedelta(days=(6 - today.weekday()) % 7 or 7)  # next Sunday

    by_id = {}
    for p in sorted((HERE / "carousels").glob("*.json")):
        c = json.loads(p.read_text(encoding="utf-8"))
        out = HERE / "out" / c.get("id", p.stem)
        slides = [out / f"slide{i}.png" for i in range(1, 5)]
        missing = [s.name for s in slides if not s.exists()]
        if missing:
            raise SystemExit(f"{c['id']}: run render.py first — missing {', '.join(missing)}")
        by_id[c["id"]] = (c, out, slides)

    if a.plan:
        plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
        selected = []
        for entry in plan:
            if entry["id"] not in by_id:
                raise SystemExit(f"plan: unknown carousel {entry['id']}")
            selected.append((by_id[entry["id"]], entry["due_at"]))
    else:
        ids = list(by_id)[:CADENCE]
        if len(ids) < CADENCE:
            print(f"note: {len(ids)} carousel(s) available, {CADENCE} slots")
        selected = []
        for i, cid in enumerate(ids):
            day = start + timedelta(days=i)
            hh, mm = (int(x) for x in TIMES[day.weekday()].split(":"))
            due = datetime(day.year, day.month, day.day, hh, mm, tzinfo=TZ)
            selected.append((by_id[cid], due.isoformat()))

    env = load_env()
    posts = []
    for (c, out, slides), due in selected:
        ig, fb = build(c)
        (out / "instagram.txt").write_text(ig + "\n", encoding="utf-8")
        (out / "facebook.txt").write_text(fb + "\n", encoding="utf-8")
        pack = {
            "id": c["id"],
            "due_at": due,
            "slides": [str(s.relative_to(HERE)) for s in slides],
            "instagram": ig,
            "facebook": fb,
            "status": "draft",
        }
        (out / "post.json").write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
        posts.append(pack)

    first = datetime.fromisoformat(posts[0]["due_at"])
    queue = {
        "week": a.name or iso_week(first),
        "timezone": "Asia/Qatar",
        "channels": {
            "instagram": env.get("BUFFER_CHANNEL_INSTAGRAM", ""),
            "facebook": env.get("BUFFER_CHANNEL_FACEBOOK", ""),
        },
        "posts": posts,
    }
    dest = HERE / a.out
    dest.mkdir(exist_ok=True)
    qpath = dest / f"week-{queue['week']}.json"
    qpath.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"week {queue['week']} -> {qpath.relative_to(HERE)}")
    for p in posts:
        n = len(p["instagram"])
        print(f"  {p['due_at'][:16].replace('T', ' ')}  {p['id']:34} ig {n:>4}/2200")


if __name__ == "__main__":
    main()
