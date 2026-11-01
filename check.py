#!/usr/bin/env python3
"""Check carousel JSON against the character limits and fact rules before rendering.

Usage: python check.py carousels/*.json
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
IMAGES = HERE / "images"

CONTACT_EN = ["+974 7713 4533", "@rahissheikhtrading"]
FORBIDDEN = re.compile(
    r"\b\d+(\.\d+)?\s?(cfm|m3|m³/h|pa|kw|hp|mm|cm|kg|%)\b", re.IGNORECASE
)

LIMITS = {"kicker": 40, "headline": 60, "subline": 90, "title": 50, "intro": 100}


def check_text(path, field, value, limit, errors, warnings):
    if value is None:
        return
    n = len(value)
    if n > limit:
        errors.append(f"{path}.{field}: {n}/{limit} chars -> {value!r}")
    elif n > limit - 3:
        warnings.append(f"{path}.{field}: {n}/{limit} chars (tight)")


def check_carousel(data, fname):
    errors, warnings = [], []

    if "needs_info" in data:
        return errors, [f"{fname}: needs_info -> {data['needs_info']}"]

    slides = data.get("slides", [])
    if not 4 <= len(slides) <= 8:
        errors.append(f"{fname}: {len(slides)} slides, expected 4-8")
    elif slides[-1].get("type") != "contact":
        errors.append(f"{fname}: last slide is not contact")

    for i, s in enumerate(slides, 1):
        p = f"{fname} slide {i}"
        if "image" in s and s["image"]:
            if not (IMAGES / s["image"]).exists():
                errors.append(f"{p}: image not in ./images -> {s['image']}")

        if s.get("type") == "hook":
            for f, lim in (("kicker", 40), ("headline", 60), ("subline", 90)):
                check_text(p, f, s.get(f), lim, errors, warnings)
            if s.get("kicker") and s["kicker"] != s["kicker"].upper():
                errors.append(f"{p}.kicker: not ALL CAPS")
            if not s.get("headline"):
                errors.append(f"{p}: hook missing headline")

        elif s.get("type") == "tier":
            if s.get("tier") not in ("S", "A", "B", "C", "D", "E", "F"):
                errors.append(f"{p}: bad tier {s.get('tier')!r}")
            check_text(p, "title", s.get("title"), 50, errors, warnings)
            check_text(p, "text", s.get("text"), 180, errors, warnings)

        elif s.get("type") == "info":
            check_text(p, "title", s.get("title"), 50, errors, warnings)
            check_text(p, "intro", s.get("intro"), 100, errors, warnings)
            items = s.get("items", [])
            if not 2 <= len(items) <= 5:
                errors.append(f"{p}: {len(items)} items, expected 2-5")
            for j, it in enumerate(items, 1):
                check_text(f"{p} item {j}", "title", it.get("title"), 40, errors, warnings)
                check_text(f"{p} item {j}", "text", it.get("text"), 110, errors, warnings)
            check_text(p, "note_title", s.get("note_title"), 40, errors, warnings)
            check_text(p, "note_text", s.get("note_text"), 110, errors, warnings)

        # contact details must never appear on a slide
        blob = " ".join(str(v) for v in json.dumps(s, ensure_ascii=False).split())
        for token in CONTACT_EN + ["info@rahistrading.com", "Birkat"]:
            if token in blob:
                errors.append(f"{p}: contact detail on slide -> {token!r}")
        for m in FORBIDDEN.finditer(blob):
            errors.append(f"{p}: invented figure -> {m.group(0)!r}")

    cap = data.get("caption_en", "")
    words = len(cap.split())
    if not 60 <= words <= 110:
        errors.append(f"{fname}: caption_en {words} words, expected 60-110")
    if "@rahissheikhtrading" not in cap:
        warnings.append(f"{fname}: caption_en does not end with the handle")
    for m in FORBIDDEN.finditer(cap):
        errors.append(f"{fname}: caption_en invented figure -> {m.group(0)!r}")

    for key, lo, hi in (("hashtags_en", 8, 12), ("hashtags_ar", 6, 10)):
        tags = data.get(key, [])
        if not lo <= len(tags) <= hi:
            errors.append(f"{fname}: {key} has {len(tags)}, expected {lo}-{hi}")
        for t in tags:
            if not t.startswith("#") or " " in t:
                errors.append(f"{fname}: bad {key} tag -> {t!r}")

    if not data.get("caption_ar"):
        errors.append(f"{fname}: missing caption_ar")
    if any("\u0000" <= ch <= "\u001f" and ch != "\n" for ch in data.get("caption_ar", "")):
        errors.append(f"{fname}: control characters in caption_ar")

    return errors, warnings


def main(paths):
    total_e = 0
    for path in sorted(paths):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        errors, warnings = check_carousel(data, Path(path).name)
        total_e += len(errors)
        status = "PASS" if not errors else "FAIL"
        print(f"[{status}] {Path(path).name}")
        for e in errors:
            print(f"    ERROR  {e}")
        for w in warnings:
            print(f"    warn   {w}")
    print(f"\n{total_e} error(s) across {len(paths)} carousel(s)")
    return 1 if total_e else 0


if __name__ == "__main__":
    args = sys.argv[1:] or [str(p) for p in sorted((HERE / "carousels").glob("*.json"))]
    sys.exit(main(args))
