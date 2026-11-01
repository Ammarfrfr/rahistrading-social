#!/usr/bin/env python3
"""Render the profile kit: avatar options, highlight covers, Facebook cover.

Usage:  python3 make_profile.py
Writes: profile/*.png
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

import render as R

HERE = Path(__file__).resolve().parent
OUT = HERE / "profile"

ICON_EXTRA = {
    "phone": ('<path d="M16 6h-4a3 3 0 0 0-3 3c0 15 12 27 27 27a3 3 0 0 0 3-3v-4l-7-2-3 5'
              'c-5-2-9-6-11-11l5-3-2-7z"/>'),
    "wrench": ('<path d="M30 6a10 10 0 0 0-9.2 13.8L7 33.6 10.4 37l13.8-13.8A10 10 0 1 0 30 6z"/>'),
}


def svg(name, size, color=R.RED, sw=2.2):
    body = {**R.ICONS, **ICON_EXTRA}[name]
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


def page(w, h, body, bg):
    return ('<!doctype html><html><head><meta charset="utf-8">'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800;900&display=swap">'
            f'<style>*{{box-sizing:border-box}}body{{margin:0;width:{w}px;height:{h}px;overflow:hidden;'
            f'background:{bg};font-family:Inter,Arial,sans-serif;-webkit-font-smoothing:antialiased}}</style>'
            f'</head><body>{body}</body></html>')


def avatar_monogram():
    return page(1080, 1080,
                f'<div style="width:1080px;height:1080px;display:flex;align-items:center;justify-content:center;'
                f'background:{R.RED}"><div style="font-size:350px;font-weight:800;letter-spacing:-16px;'
                f'color:#fff;line-height:1;transform:translateY(-8px)">RST</div></div>', R.RED)


def avatar_air():
    return page(1080, 1080,
                f'<div style="width:1080px;height:1080px;display:flex;align-items:center;justify-content:center;'
                f'background:{R.INK}">{svg("air", 560, "#fff", 2.0)}</div>', R.INK)


def highlight(icon_name):
    """Story-sized (1080x1920); Instagram crops the centre 1080px circle."""
    return page(1080, 1920,
                f'<div style="width:1080px;height:1920px;display:flex;align-items:center;justify-content:center;'
                f'background:{R.PAPER};position:relative">'
                f'<div style="position:absolute;width:1000px;height:1000px;border:3px solid {R.LINE};'
                f'border-radius:50%"></div>{svg(icon_name, 760, R.RED, 1.9)}</div>', R.PAPER)


def fb_cover():
    return page(1640, 856,
                f'<div style="width:1640px;height:856px;background:{R.INK};display:flex;align-items:center;'
                f'justify-content:center">'
                f'<div style="width:640px;text-align:center">'
                f'<div style="font-size:24px;font-weight:800;letter-spacing:6px;color:{R.RED};margin-bottom:26px">'
                f'RAHIS SHEIKH TRADING &middot; DOHA</div>'
                f'<div style="font-size:62px;line-height:1.1;font-weight:800;color:#fff;margin-bottom:26px">'
                f'Kitchen exhaust, planned, built and installed.</div>'
                f'<div style="font-size:28px;line-height:1.45;color:#D9D9D9">Hoods &middot; Ducts &middot; Fans '
                f'&middot; Stainless fabrication</div>'
                f'<div style="margin-top:34px;font-size:26px;font-weight:700;color:#fff">'
                f'+974 7713 4533 &nbsp;&middot;&nbsp; rahistrading.com</div>'
                f'</div></div>', R.INK)


def main():
    OUT.mkdir(exist_ok=True)
    jobs = [
        ("avatar-monogram.png", avatar_monogram()),
        ("avatar-airflow.png", avatar_air()),
        ("fb-cover.png", fb_cover()),
        ("hl-fans.png", highlight("fan")),
        ("hl-ducts.png", highlight("duct")),
        ("hl-hoods.png", highlight("hood")),
        ("hl-fabrication.png", highlight("wrench")),
        ("hl-installation.png", highlight("check")),
        ("hl-contact.png", highlight("phone")),
    ]
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name, html in jobs:
            pg = browser.new_page(viewport={"width": 1640, "height": 1920})
            pg.set_content(html, wait_until="load")
            pg.evaluate("document.fonts.ready")
            pg.screenshot(path=str(OUT / name), clip=_clip(html))
            pg.close()
            print("wrote", (OUT / name).relative_to(HERE))
        browser.close()


def _clip(html):
    import re
    m = re.search(r"body\{margin:0;width:(\d+)px;height:(\d+)px", html)
    return {"x": 0, "y": 0, "width": int(m.group(1)), "height": int(m.group(2))}


if __name__ == "__main__":
    main()
