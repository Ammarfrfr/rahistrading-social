# Rahis — exhaust carousel batch (rendered)

Five carousels, 20 slides at 1080×1350, plus caption files. Built with the `render.py`
pipeline, so layout and contact details are fixed and only the copy lives in JSON.

| Carousel | Topic | Structure |
| --- | --- | --- |
| `02-parts-of-an-exhaust-system` | Hood, duct, fan | anatomy, 3 + 3 items |
| `03-axial-vs-centrifugal-fans` | Axial vs centrifugal roof fans | comparison, 3 + 3 |
| `04-stainless-vs-gi` | Stainless vs GI | decision guide, 3 + 3 |
| `05-five-warning-signs` | Five signs ventilation is failing | checklist, 3 + 2 |
| `07-plan-to-installation` | Plan to installation | process, 4 + 3 |

Topic 01 is the published post. Topic 06 (maintenance checklist) is deliberately held
back — it repeats the warning signs in 05 and belongs in next Saturday's batch.

Each `out/<id>/` contains `slide1–4.png`, `caption_en.txt`, `caption_ar.txt`,
`instagram.txt` and `facebook.txt` (bilingual post copy with hashtags, ready to paste),
plus `post.json` for the scheduler. See `docs/automation-setup.md`.

## Commands

```bash
cd ~/Project_shit/rahistrading-social
python3 check.py                                   # limits, facts, image names
python3 measure.py carousels/0*.json               # real vertical slack per slide
python3 render.py carousels/02-*.json --images ./images
python3 make_pack.py                               # captions per platform + week queue
python3 make_profile.py                            # avatar, highlight covers, FB cover
python3 studio.py                                  # review page -> http://127.0.0.1:8765
python3 cloudinary_upload.py --id 06-grease-and-fire
python3 publish_buffer.py --check                  # dry run; --live to schedule
python3 cleanup_cloudinary.py --live               # delete images 3 days after publish
```

Playwright and its Chromium build are already installed on this machine.

## Two things the pipeline does not catch

**1. `render.py` can miss overlap.** It compares `scrollHeight` to `clientHeight`. But the
slide root is `justify-content: space-between` in a fixed-height box, so when content
overruns, the children overlap the header instead of pushing past the bottom — and
`scrollHeight` stays at 1350, so no warning prints. That happened on six slides in the
first pass (the brand line sat on top of the photo). `measure.py` checks actual gaps
between children; treat any slide with slack under 20px or min-gap under 10px as broken.
All 20 slides now report `ok`.

**2. `render.py` cannot stop invented facts.** `check.py` does: it fails on any figure
(`cfm`, `pa`, `kw`, `hp`, `mm`, `%`…), on contact details appearing on a slide, and on
image names missing from `./images`.

## Copy notes

- Hook, info and contact copy are all within Claude's limits; `check.py` passes all five.
- Contact slides carry a per-post CTA headline and subline (`render.py` reads these from
  the contact slide). Without them, all five posts end with the same generic line.
- Text was shortened until nothing overlapped. When editing later, re-run `measure.py`
  rather than trusting the renderer's warning.
- `reference/example_carousel_01.json` is the approved style example, kept out of
  `carousels/` so `check.py` does not treat it as part of the batch.

## Images

Renamed copies of the client's own photos, so nothing needs a stock licence:

`hood.jpg` `hood-filters.jpg` `duct.jpg` `duct-alt.jpg` `fan.jpg` `fan-motor.jpg`
`fan-roof.jpg` `welding.jpg` `install.jpg` `workshop.jpg`

Framing rule: photos are **contained, never centre-cropped**. Hook photos scale to fit
(max height 560px) on the dark slide; info photos sit in a bordered card capped at
350×438. Portrait sources (0.45–0.75) therefore show their full subject instead of the
middle slice that `object-fit: cover` used to produce. Decorative line-art (airflow,
fan, check) is drawn inline in `render.py` — original vectors, no third-party assets.

Excluded on purpose: the orange "Rahis Sheikh Trading" posters (old numbers), the
"RS Trading" catalogue pages (watermarks, another company's name), and phone screenshots
with UI chrome. `duct-alt.jpg` now carries 05 slide 3.

## Brand

Both accounts are **@rahissheikhtrading** — <https://facebook.com/rahissheikhtrading> and
<https://instagram.com/rahissheikhtrading> — which matches `RAHIS SHEIKH TRADING` on the
slides and the handle in every caption. Nothing to change in `render.py`.

The Instagram display name still reads "Rahis Kitchen Equipments"; the slides and Page say
"Rahis Sheikh Trading". Align the display name to the Page (see `profile/README.md`).
