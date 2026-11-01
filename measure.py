#!/usr/bin/env python3
"""Measure real vertical slack per slide.

render.py only compares scrollHeight to clientHeight, which misses the case where
`justify-content: space-between` has negative free space and the children overlap
instead of pushing past the bottom. This reports actual gaps between children.
"""
import json
import sys
from pathlib import Path

import render as R


def main(paths):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        for path in paths:
            c = json.loads(Path(path).read_text(encoding="utf-8"))
            s = c["slides"]
            total = len(s)
            pages = []
            for i, sl in enumerate(s, 1):
                k = sl.get("type")
                if k == "hook":
                    pages.append(R.hook(sl, R.load_img(sl.get("image"), "images"), total))
                elif k == "info":
                    pages.append(R.info(sl, i, R.load_img(sl.get("image"), "images"), total))
                elif k == "tier":
                    pages.append(R.tier(sl, i, total))
                else:
                    pages.append(R.contact(sl, total))
            print(f"\n{Path(path).name}")
            for i, p in enumerate(pages, 1):
                page.set_content(R.wrap(p), wait_until="load")
                page.evaluate("document.fonts.ready")
                report = page.evaluate(
                    """() => {
                        const el = document.getElementById('s');
                        const cs = getComputedStyle(el);
                        const pad = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
                        const kids = [...el.children].map(k => {
                            const r = k.getBoundingClientRect();
                            return {top: Math.round(r.top), bottom: Math.round(r.bottom), h: Math.round(r.height)};
                        });
                        let worst = 9999;
                        for (let j = 0; j < kids.length - 1; j++) worst = Math.min(worst, kids[j+1].top - kids[j].bottom);
                        const used = kids.reduce((a, k) => a + k.h, 0) + pad;
                        return {slack: Math.round(1350 - used), gap: worst, kids: kids.length};
                    }"""
                )
                flag = "OVERLAP" if report["gap"] < 4 else ("tight" if report["slack"] < 24 else "ok")
                print(
                    f"  slide {i}: slack {report['slack']:>4}px  min-gap {report['gap']:>4}px  "
                    f"children {report['kids']}  {flag}"
                )
        browser.close()


if __name__ == "__main__":
    args = sys.argv[1:] or [str(p) for p in sorted(Path("carousels").glob("*.json"))]
    main(args)
