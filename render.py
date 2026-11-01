#!/usr/bin/env python3
"""Render a Rahis carousel JSON into 4 PNG slides (1080x1350) + caption files.

Setup (once):  pip install playwright && playwright install chromium
Usage:         python render.py carousel.json [--images ./images] [--out ./out] [--html-only]

The contact slide details are hard-coded below, so the AI never writes them.
"""
import argparse, base64, html, json, mimetypes, sys
from pathlib import Path

RED, INK, SOFT, PAPER, LINE = "#AF1A1F", "#1E1F21", "#4A4B4D", "#F6F5F3", "#D8D5D0"
DOT_GRID = "background-image:radial-gradient(#E8E4DD 1.2px,transparent 1.2px);background-size:38px 38px"
BRAND = "RAHIS SHEIKH TRADING"
CONTACT = [
    ("PHONE", "+974 7713 4533"),
    ("ADDRESS", "Birkat Al Awamer, GWC Warehouse, B3, A4, 37, Doha, Qatar"),
    ("SOCIAL MEDIA", "@rahissheikhtrading"),
    ("PLATFORMS", "Instagram and Facebook"),
]
TIER_COLORS = {"S": "#F0565B", "A": "#F2A15C", "B": "#F5E663", "C": "#7ED957",
               "D": "#7FB3F0", "E": "#9B8CF0", "F": "#F26BC8"}
LIMITS = {"tier_text": 180, "kicker": 40, "headline": 60, "subline": 90, "title": 50, "intro": 100,
          "item_title": 40, "item_text": 110, "note_title": 40, "note_text": 110}


def esc(s):
    return html.escape(s or "")


def err(msg):
    sys.exit("ERROR: " + msg)


# ---- original vector accents (inline SVG line art, no stock assets) ----
def _blades():
    b = ('<path d="M24 20.8c.5-6.4 2.7-9.9 6.4-9.5 3.3.3 4.9 3.1 3.7 5.8'
         '-1.2 2.8-4.7 3.9-7.9 3.7"/>')
    return "".join(f'<g transform="rotate({a} 24 24)">{b}</g>' for a in (0, 120, 240))


ICONS = {
    "fan": _blades() + '<circle cx="24" cy="24" r="2.6"/>',
    "duct": ('<rect x="7" y="17" width="27" height="14" rx="1.5"/>'
             '<path d="M14 17v14M27 17v14"/><path d="M34 24h8m-4.5-4.5L42 24l-4.5 4.5"/>'),
    "hood": '<path d="M9 20l15-9 15 9v3H9z"/><path d="M14 32h20M17 23v9M31 23v9"/>',
    "air": ('<path d="M6 16h20c4.2 0 6.8-2 6.8-4.9 0-2.6-1.9-4.4-4.3-4.4"/>'
            '<path d="M6 24h26c4 0 6.5 2 6.5 4.8 0 2.6-1.8 4.4-4.2 4.4"/>'
            '<path d="M6 32h16c3.4 0 5.6 1.8 5.6 4.4 0 2.2-1.6 3.8-3.8 3.8"/>'),
    "check": '<path d="M10 25l9 9 19-20"/>',
}


def icon(name, size=40, color=RED, sw=2.4, op=1):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" opacity="{op}" '
            f'style="display:block;flex:none">{ICONS[name]}</svg>')


def check(d, key, where, required=False):
    v = d.get(key)
    if not v:
        if required:
            err(f"{where}: '{key}' is required")
        return
    limit = LIMITS.get(key.replace("item_", "item_"), 999)
    if len(v) > limit:
        err(f"{where}: '{key}' is {len(v)} characters, max {limit}. Ask the AI to shorten it.")


def validate(c):
    s = c.get("slides")
    if not isinstance(s, list) or len(s) < 4:
        err("slides need at least 4 pages: hook, ... , contact")
    if s[0].get("type") != "hook" or s[-1].get("type") != "contact":
        err("slides must start with hook and end with contact")
    for k in ("caption_en", "caption_ar", "hashtags_en", "hashtags_ar"):
        if not c.get(k):
            err(f"missing '{k}'")
    for k in ("hashtags_en", "hashtags_ar"):
        if not all(h.startswith("#") and " " not in h for h in c[k]):
            err(f"every item in {k} must start with # and contain no spaces")
    h = s[0]
    for k in ("kicker", "headline", "subline"):
        check(h, k, "slide 1", required=(k != "kicker"))
    for n, sl in enumerate(s[1:-1], 2):
        w = f"slide {n}"
        if sl.get("type") == "tier":
            check(sl, "title", w, True)
            check(sl, "text", w, True)
            if sl.get("tier") not in TIER_COLORS:
                err(f"{w}: 'tier' must be one of {', '.join(TIER_COLORS)}")
            continue
        if sl.get("type") != "info":
            err(f"{w}: type must be 'info' or 'tier'")
        check(sl, "title", w, True)
        check(sl, "intro", w)
        check(sl, "note_title", w)
        check(sl, "note_text", w)
        items = sl.get("items", [])
        if not 2 <= len(items) <= 5:
            err(f"{w}: needs 2 to 5 items")
        for i, it in enumerate(items, 1):
            check({"item_title": it.get("title")}, "item_title", f"{w} item {i}", True)
            check({"item_text": it.get("text")}, "item_text", f"{w} item {i}")


def load_img(name, folder):
    if not name:
        return None
    p = Path(folder) / name
    if not p.exists():
        err(f"image '{name}' not found in {folder}")
    mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def root(bg, parts, style=""):
    return (f'<div id="s" style="width:1080px;height:1350px;box-sizing:border-box;padding:72px;display:flex;'
            f'flex-direction:column;justify-content:space-between;font-family:Inter,Arial,sans-serif;background:{bg};{style}">'
            + "".join(parts) + "</div>")


def header(n, dark, total=4):
    c1, c2 = ("#fff", "#D9D9D9") if dark else (RED, SOFT)
    return (f'<div style="display:flex;justify-content:space-between;align-items:center"><div style="font-size:26px;'
            f'font-weight:800;letter-spacing:4px;color:{c1}">{BRAND}</div><div style="font-size:26px;font-weight:500;'
            f'color:{c2}">{n} / {total}</div></div>')


def pic(src, h, bg="transparent"):
    """Show the whole photo, never a centre slice: scale to fit, centred on the slide tone."""
    return (f'<div style="height:{h}px;display:flex;align-items:center;justify-content:center;background:{bg}">'
            f'<img src="{src}" style="max-width:100%;max-height:{h}px;width:auto;height:auto;display:block;'
            f'border-radius:6px"></div>')


def photo_card(src, w, h):
    """Framed photo for info slides — contain, so the subject is never cropped."""
    return (f'<div style="flex:none;background:#EDEAE4;border:1px solid {LINE};border-radius:6px;'
            f'overflow:hidden;display:flex"><img src="{src}" style="max-width:{w}px;max-height:{h}px;'
            f'width:auto;height:auto;object-fit:contain;display:block"></div>')



def hook(s, img, total=4):
    n = len(s["headline"])
    size = (120 if n <= 36 else 100) if not img else (88 if n <= 36 else 76)
    sub = 40 if not img else 34
    kicker = (f'<div style="display:flex;align-items:center;gap:18px;margin-bottom:24px">'
              f'{icon("air", 34, "#fff", 2.8, .9)}'
              f'<div style="font-size:28px;font-weight:700;letter-spacing:5px;color:#fff">'
              f'{esc(s.get("kicker"))}</div></div>') if s.get("kicker") else ""
    body = (f'<div><div style="width:96px;height:8px;background:{RED};margin-bottom:36px"></div>{kicker}'
            f'<h1 style="margin:0;font-size:{size}px;line-height:1.05;font-weight:800;color:#fff">{esc(s["headline"])}</h1>'
            f'<p style="margin:36px 0 0;font-size:{sub}px;line-height:1.4;color:#D9D9D9">{esc(s["subline"])}</p></div>')
    foot = ('<div style="display:flex;justify-content:space-between;align-items:center;border-top:2px solid #4A4B4D;'
            'padding-top:32px;font-size:28px;color:#D9D9D9"><div>Doha, Qatar</div>'
            '<div style="font-weight:700;color:#fff">Swipe \u2192</div></div>')
    return root(INK, [header(1, True, total), body] + ([pic(img, 560)] if img else []) + [foot])


def info(s, n, img, total=4):
    items = s["items"]
    tight = len(items) > 3 or bool(img)
    tsz, dsz, pad, circ = (40, 30, 24, 60) if tight else (44, 32, 40, 72)
    all_text = all(i.get("text") for i in items)
    rows = ""
    for idx, it in enumerate(items, 1):
        mark = (f'<div style="flex:none;width:{circ}px;height:{circ}px;border-radius:{circ // 2}px;background:{RED};'
                f'color:#fff;font-size:28px;font-weight:800;display:flex;align-items:center;justify-content:center">{idx}</div>'
                if all_text else f'<div style="flex:none;width:20px;height:20px;background:{RED};margin-top:14px"></div>')
        txt = (f'<div style="font-size:{dsz}px;line-height:1.45;color:{SOFT};margin-top:10px">{esc(it["text"])}</div>'
               if it.get("text") else "")
        rows += (f'<div style="display:flex;gap:30px;align-items:flex-start;padding:{pad}px 0;border-top:2px solid {LINE}">'
                 f'{mark}<div><div style="font-size:{tsz}px;font-weight:800;color:{INK}">{esc(it["title"])}</div>{txt}</div></div>')
    hsz = 84 if len(s["title"]) <= 34 else 72
    if img:
        hsz = min(hsz, 62)
    intro = (f'<p style="margin:0 0 28px;font-size:34px;line-height:1.4;color:{SOFT}">{esc(s["intro"])}</p>'
             if s.get("intro") else "")
    head = (f'<div><h2 style="margin:0 0 {20 if s.get("intro") else 28}px;font-size:{hsz}px;line-height:1.08;'
            f'font-weight:800;color:{INK}">{esc(s["title"])}</h2>{intro}</div>')
    top = (f'<div style="display:flex;gap:34px;align-items:center;margin-bottom:18px">{head}'
           f'{photo_card(img, 350, 370 if (s.get("note_title") or s.get("note_text")) else 438)}</div>'
           if img else head)
    main = f'<div>{top}{rows}</div>'
    if s.get("note_title") or s.get("note_text"):
        note_head = (f'<div style="display:flex;align-items:center;gap:14px;margin-bottom:10px">'
                     f'{icon("check", 26, "#fff", 2.6, .9)}<div style="font-size:30px;font-weight:800;'
                     f'color:#fff">{esc(s.get("note_title"))}</div></div>'
                     if s.get("note_title") else "")
        bottom = (f'<div style="background:{INK};padding:36px 44px;border-radius:6px">{note_head}'
                  f'<div style="font-size:28px;line-height:1.5;color:#D9D9D9">{esc(s.get("note_text"))}</div></div>')
    else:
        bottom = (f'<div style="border-top:2px solid {LINE};padding-top:32px;font-size:28px;color:{SOFT}">'
                  f'Rahis Sheikh Trading \u00b7 Doha, Qatar</div>')
    return root(PAPER, [header(n, False, total), main, bottom], style=DOT_GRID)


def tier(s, n, total=4):
    """Tier-list page: S/A/B/C/D/E/F block, claim, one paragraph."""
    color = TIER_COLORS[s["tier"]]
    head = (f'<div style="background:{color};border-radius:10px;padding:46px 52px;display:flex;'
            f'align-items:center;justify-content:space-between;margin-bottom:44px">'
            f'<div style="font-size:210px;line-height:.78;font-weight:900;color:{INK}">{s["tier"]}</div>'
            f'<div style="font-size:26px;font-weight:800;letter-spacing:7px;color:{INK};opacity:.55">TIER</div>'
            f'</div>')
    chips = "".join(
        f'<div style="flex:1;text-align:center;padding:16px 0;border-radius:8px;font-size:34px;font-weight:800;'
        f'background:{TIER_COLORS[k] if k == s["tier"] else "transparent"};'
        f'color:{INK if k == s["tier"] else SOFT};'
        f'border:2px solid {TIER_COLORS[k] if k == s["tier"] else LINE};'
        f'opacity:{1 if k == s["tier"] else .55}">{k}</div>' for k in "SABCDEF")
    body = (f'<div>{head}<h2 style="margin:0 0 26px;font-size:84px;line-height:1.06;font-weight:800;'
            f'color:{INK}">{esc(s["title"])}</h2>'
            f'<p style="margin:0 0 44px;font-size:40px;line-height:1.42;color:{SOFT}">{esc(s["text"])}</p>'
            f'<div style="display:flex;gap:10px">{chips}</div></div>')
    foot = (f'<div style="border-top:2px solid {LINE};padding-top:32px;font-size:28px;color:{SOFT}">'
            f'Rahis Sheikh Trading \u00b7 Doha, Qatar</div>')
    return root(PAPER, [header(n, False, total), body, foot], style=DOT_GRID)


def contact(s, total=4):
    head = s.get("headline") or "Planning or upgrading your kitchen exhaust?"
    sub = s.get("subline") or "Talk to the team at Rahis Sheikh Trading."
    rows = "".join(
        f'<div style="padding:26px 0;border-top:2px solid #E3E0DB"><div style="font-size:24px;font-weight:700;'
        f'letter-spacing:3px;color:#6B6B6B;margin-bottom:8px">{l}</div><div style="font-size:38px;font-weight:700;'
        f'line-height:1.3;color:{INK}">{esc(v)}</div></div>' for l, v in CONTACT)
    body = (f'<div><h2 style="margin:0 0 20px;font-size:76px;line-height:1.08;font-weight:800;color:#fff">{esc(head)}</h2>'
            f'<p style="margin:0 0 44px;font-size:36px;line-height:1.4;color:#fff">{esc(sub)}</p>'
            f'<div style="background:#fff;padding:20px 48px;border-radius:6px">{rows}</div></div>')
    note = (f'<div style="display:flex;align-items:center;gap:14px">{icon("air", 26, "#fff", 2.6, .9)}'
            f'<div style="font-size:28px;font-weight:500;color:#fff">rahistrading.com</div></div>')
    return root(RED, [header(4, True, total), body, note])


def wrap(body):
    return ('<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="https://fonts.googleapis.com/'
            'css2?family=Inter:wght@400;500;700;800&display=swap"><style>body{margin:0}</style></head><body>'
            + body + "</body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file")
    ap.add_argument("--images", default="images")
    ap.add_argument("--out", default="out")
    ap.add_argument("--html-only", action="store_true", help="write HTML only (no PNG, no browser needed)")
    a = ap.parse_args()

    c = json.loads(Path(a.json_file).read_text(encoding="utf-8"))
    if c.get("needs_info"):
        err("the AI asked for more information first: " + str(c["needs_info"]))
    validate(c)
    s = c["slides"]
    total = len(s)
    pages = []
    for i, sl in enumerate(s, 1):
        kind = sl.get("type")
        if kind == "hook":
            pages.append(hook(sl, load_img(sl.get("image"), a.images), total))
        elif kind == "info":
            pages.append(info(sl, i, load_img(sl.get("image"), a.images), total))
        elif kind == "tier":
            pages.append(tier(sl, i, total))
        elif kind == "contact":
            pages.append(contact(sl, total))
        else:
            err(f"slide {i}: unknown type {kind!r}")

    out = Path(a.out) / c.get("id", "carousel")
    out.mkdir(parents=True, exist_ok=True)
    (out / "caption_en.txt").write_text(c["caption_en"].strip() + "\n\n" + " ".join(c["hashtags_en"]) + "\n", encoding="utf-8")
    (out / "caption_ar.txt").write_text(c["caption_ar"].strip() + "\n\n" + " ".join(c["hashtags_ar"]) + "\n", encoding="utf-8")

    if a.html_only:
        for i, p in enumerate(pages, 1):
            (out / f"slide{i}.html").write_text(wrap(p), encoding="utf-8")
        print("HTML written to", out)
        return

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        for i, p in enumerate(pages, 1):
            page.set_content(wrap(p), wait_until="load")
            page.evaluate("document.fonts.ready")
            over = page.evaluate("(() => {const e=document.getElementById('s'); return e.scrollHeight - e.clientHeight})()")
            if over > 2:
                print(f"WARNING: slide {i} overflows by {over}px. Ask the AI to shorten the text.")
            page.screenshot(path=str(out / f"slide{i}.png"))
        browser.close()
    print("Done:", out)


if __name__ == "__main__":
    main()
