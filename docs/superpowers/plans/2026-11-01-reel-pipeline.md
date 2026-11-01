# Reel Pipeline (`reel.py`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `reel.py` — a recipe-driven pipeline that turns the client's WhatsApp clips into 30–40s, 1080×1920 Instagram Reels with Arabic-first on-screen text, a music bed, and paste-ready captions, producing two review variants (hook with faces + fan-photo end card / hook without faces + HTML brand card).

**Architecture:** One flat script `reel.py` in the house style of `render.py`: load JSON recipe → validate → build timeline → render text overlays to transparent PNGs with Playwright (Arabic needs a real webfont + RTL, never ffmpeg `drawtext`) → normalise every video segment with ffmpeg → concat → composite overlays → mix audio (music primary, site audio at −12 dB) → loudnorm → write `out/<id>-<variant>/` (reel.mp4 + captions + manifest). Tests use stdlib `unittest` with synthetic ffmpeg clips, so no test depends on the WhatsApp files.

**Tech Stack:** Python 3 (stdlib only), ffmpeg 9.0.2 (installed), Playwright + Chromium (installed), Google Fonts `IBM Plex Sans Arabic` + `Inter`.

**Spec:** `docs/superpowers/specs/2026-11-01-reel-pipeline-design.md` (approved 2026-11-01 — the plan argues from it; executors read both.)

## Global Constraints

- Output: **1080×1920, 30 fps CFR, h264 yuv420p + aac 48kHz stereo**; total duration **30–40s** (recipe timeline is 32.0s: 27s footage + 5s end card).
- Audio mix: **music is the primary layer**; site audio pre-attenuated to `site_audio_db: -12` dB; `amix ... normalize=0` (ffmpeg ≥4.4; we have 9.0.2); final single-pass `loudnorm=I=-14:TP=-1.5:LRA=11`.
- Music is user-supplied under `data/music/`: recipe `"music"` names a missing file → **validation error**; `"music": null` → **warning, build proceeds with site audio only, print a note** (design: pipeline never blocks on music).
- No invented figures anywhere (on-screen or captions): reuse `check.FORBIDDEN` regex (`reel.py` does `from check import FORBIDDEN`; `check.py` is import-safe).
- Captions follow house rules: `caption_en` 60–110 words, `hashtags_en` 8–12, `hashtags_ar` 6–10, no figures, ends with `@rahissheikhtrading`; combined `instagram.txt` = **Arabic first, English second, `———` divider, `📍 Doha, Qatar` line, deduped hashtags, ≤ 2200 chars** (`make_pack.IG_LIMIT` — import the constants `from make_pack import DIVIDER, IG_LIMIT`; do not touch `make_pack.py`'s behaviour).
- Arabic on screen: **IBM Plex Sans Arabic + Inter via Google Fonts, `dir="rtl"`**, rendered by Playwright to transparent PNGs. Never `drawtext`. Mixed bidi: Latin handle/📍 lines get their own `dir="ltr"` span.
- Every overlay PNG carries a bottom gradient scrim (transparent PNG) so text reads on light footage and on the fan photo.
- Assets pinned to the audited files: `data/WhatsApp Video 2026-10-26 at 19.08.47.mp4` (kitchen), `data/WhatsApp Video 2026-10-27 at 23.09.47.mp4` (site), `data/WhatsApp Image 2026-10-26 at 19.08.53.jpeg`. The 2-second clip is excluded.
- Output layout: `out/<id>-<variant>/` containing `reel.mp4`, `instagram.txt`, `caption_ar.txt`, `caption_en.txt`, `post.json`.
- **Untouched:** `make_pack.py`, `render.py`, `check.py`, `studio.py`, `schedule/`, `cloudinary_upload.py`, `publish_buffer.py` (import constants only, never modify).
- Repo is **not a git repo yet** (verified); tests run with stdlib: `python3 -m unittest discover -s tests -v` (no pytest).
- Copy rules from `strategy.md`: hook = one specific claim, no selling in line one, **one CTA**, no figures.

## Review Focus

1. **Arabic overlays render shaped/RTL (or silently fall back to tofu/Latin).** → Task 2 tests assert font link, `dir="rtl"`, bidi spans, and that Playwright produces non-empty PNGs; Task 6 visually verifies frame strips.
2. **Audio mix paths: music present vs `"music": null`** — one must mix two streams at −12 dB site, the other must still produce a valid reel with a printed note. → Task 5 tests both paths on synthetic audio.
3. **Timing drift from the broken source** (site clip is 29.83fps with non-monotonic DTS) — output must still be exactly 30 fps CFR with duration matching the recipe ±0.2s. → Task 4 probes fps/duration; Task 5 asserts final duration tolerance.
4. **Variant A/B differ only where intended** (hook shot + end card; B's hook must contain no identifiable person; shared beats identical). → Task 2 timeline tests pin both variants' segments; Task 6 does a frame-strip face check on B's hook.
5. **IG-spec output: right resolution, no clipped audio, captions paste-ready.** → Task 5 probes 1080×1920/audio stream, `volumedetect` max ≤ −0.5 dB, `instagram.txt` ≤ 2200 with Arabic first; Task 6 measures real loudness ≈ −14 LU ±2.

---

## File Structure

| File | Responsibility |
|---|---|
| Create: `reel.py` | Everything: load/validate recipe, timeline, overlay HTML + Playwright render, ffmpeg prep + assemble, caption/manifest outputs, CLI (`--check`, `--variant`). |
| Create: `reels/01-kitchen-reel.json` | The real recipe: sources, shots, beats, overlay copy (pinned below), captions, both variants. |
| Create: `tests/test_reel_validate.py` | Validation + `build_instagram` unit tests. |
| Create: `tests/test_reel_timeline.py` | Timeline/variant tests against the real recipe. |
| Create: `tests/test_reel_render.py` | Overlay/card HTML + Playwright PNG tests. |
| Create: `tests/test_reel_assemble.py` | Synthetic-ffmpeg segment prep + final assembly tests. |
| Create: `data/music/` | Drop zone for the partner's track (recipe ships `"music": null`). |
| Modify: `README.md` | Reel commands + the two known-limit notes (mirrors existing Commands block). |

Every test file starts with:
```python
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```

## Exact recipe values (copy into `reels/01-kitchen-reel.json`)

Sources: `"kitchen": "data/WhatsApp Video 2026-10-26 at 19.08.47.mp4"`, `"site": "data/WhatsApp Video 2026-10-27 at 23.09.47.mp4"`.

Shots (source window, seconds — implementer may nudge ±0.5s during Task 6 visual pass):

| shot | source | start–end (dur) | content |
|---|---|---|---|
| `hook_face` | kitchen | 5.0–8.0 (3.0) | hood + range row, worker in frame (variant A) |
| `hook_clean` | kitchen | 11.0–14.0 (3.0) | filter/hood close-up, no person (variant B) |
| `site_in` | site | 1.5–6.5 (5.0) | dark ceiling ducts ("before") |
| `work` | site | 17.0–23.0 (6.0) | workers fitting panels |
| `detail` | kitchen | 14.5–17.5 (3.0) | hood/grease-filter detail |
| `pay_a` | kitchen | 17.5–21.5 (4.0) | pots, range, extinguisher |
| `pay_b` | kitchen | 0.5–4.0 (3.5) | counters + dough sheeter |
| `pay_c` | kitchen | 8.5–11.0 (2.5) | range line |

Timeline (in order): `hook` beat (3.0) → `site_in` (5.0) → `work` (6.0) → `detail` (3.0) → `pay_a` (4.0) → `pay_b` (3.5) → `pay_c` (2.5) → **end card (5.0)** = **32.0s**. The hook shot comes from `variants[].hook`; beats 2–7 are shared.

Overlays (absolute windows on the final timeline): `hook` 0–3, `before` 3–8, `work` 8–14, `detail` 14–17, `payoff` 17–27. Rule (not recipe data): if `endcard.type == "image"`, append a `cta` overlay window 27–32 rendered over the photo; if `"card"`, the card PNG already has the CTA baked in.

**Overlay copy** (Arabic big 96px / English small 44px under a red `#AF1A1F` bar; text block left/right 64px, bottom 220px, `dir="rtl"`):

| id | ar | en |
|---|---|---|
| `hook` | مطبخ من الموقع إلى التشغيل | From bare site to running kitchen |
| `before` | قبل — كان الموقع مجرد حديد | Before — bare steel and ductwork |
| `work` | التركيب | On site |
| `detail` | فلاتر الدهون والشفاط | Hood and grease filters |
| `payoff` | المطبخ جاهز للتشغيل | Ready to cook |
| `cta` | مطبخك يحتاج شفاطًا أو تهوية؟ اسألني في التعليقات 👇 | Questions about your kitchen's airflow? Ask below. |

**End card:** `card` (HTML, 1080×1920, `#1E1F21` ink background, dot-grid, brand header `RAHIS SHEIKH TRADING`, cta copy above, handle `@rahissheikhtrading` + `📍 Doha, Qatar` in an LTR span) | `image` (the fan photo, contain-centred on a boxblurred copy of itself, with the `cta` overlay window on top).

**Variants:** `{"name": "a", "hook": "hook_face", "endcard": {"type": "image", "image": "data/WhatsApp Image 2026-10-26 at 19.08.53.jpeg"}}`, `{"name": "b", "hook": "hook_clean", "endcard": {"type": "card"}}`. Output dirs: `out/01-kitchen-reel-a/`, `out/01-kitchen-reel-b/`.

**Captions** (pinned; both must pass the Global Constraints):

`caption_en`:
```
A commercial kitchen is three parts working as one: the hood over the line, the duct that carries, and the fan that pulls. Miss one and the room never clears.

This reel follows one job from the bare site to the finished kitchen — steel fabricated, duct routed, hood hung, filters in, ready for service.

If your kitchen fills with smoke and never clears, send us the layout and we will check all three.

Call +974 7713 4533 or message @rahissheikhtrading
```

`caption_ar`:
```
المطبخ التجاري ثلاثة أجزاء تعمل كوحدة: الشفاط فوق خط الطبخ، والمجرى الذي يحمل الهواء، والمروحة التي تسحبه. لو نقص واحد، الغرفة ما تتنظف.

في هذا الفيديو نمشي معكم من الموقع الخام إلى المطبخ الجاهز — نحاس مصنّع، مجرى مرتب، شفاط مركّب، فلاتر داخلة، جاهز للتشغيل.

إذا مطبخك يمتلئ دخان ولا ينفتح، أرسل لنا التخطيط ونفحص الثلاثة معًا.

اتصل +974 7713 4533 أو راسل @rahissheikhtrading
```

`hashtags_en` (10): `#RahisSheikhTrading #KitchenExhaust #CommercialKitchen #KitchenVentilation #Ductwork #ExhaustHood #RestaurantKitchen #Doha #Qatar #HospitalityDesign`
`hashtags_ar` (6): `#تهوية_المطابخ #شفاطات_مطابخ #مطابخ_تجارية #مطاعم_قطر #قطر #دوحة`

Other recipe fields: `"id": "01-kitchen-reel"`, `"music": null` (partner drops a file in `data/music/` and names it here), `"site_audio_db": -12`.

---

### Task 1: Git baseline, recipe, validation + `--check`

**Files:**
- Create: `reel.py` (first slice: load/validate/CLI)
- Create: `reels/01-kitchen-reel.json`
- Create: `tests/test_reel_validate.py`

**Interfaces:**
- Produces (later tasks rely on these exact names):
  - `load_recipe(path: str | Path) -> dict` — reads JSON, returns dict.
  - `validate_recipe(recipe: dict, here: Path) -> tuple[list[str], list[str]]` — `(errors, warnings)`; empty errors = valid. Checks, in order: `id` present; every `sources[*]` path exists under `here`; every shot's `source` key exists and `0 ≤ start < end`; every beat's `shot` exists; every variant's `hook` and `endcard` exist and `endcard.type in ("image", "card")` (image mode: `endcard.image` exists); every overlay `from ≥ 0`, `dur > 0`, and `from + dur ≤ 32.0`; overlay + endcard `ar`/`en` text run through `check.FORBIDDEN` (errors: `invented figure -> ...`); captions: `caption_en` 60–110 words, `hashtags_en` 8–12 / `hashtags_ar` 6–10 each starting `#` with no spaces, `caption_ar` non-empty, `caption_en` contains `@rahissheikhtrading`; music: `"music" is None` → warning `"no music track — building with site audio only"` else missing file → error.
  - `build_instagram(recipe: dict) -> str` — `caption_ar.strip() + DIVIDER + caption_en.strip() + "\n\n\U0001F4CD Doha, Qatar" + "\n\n" + deduped( hashtags_ar + hashtags_en )`; raises `SystemExit` with message if `len > IG_LIMIT`.
  - CLI: `python3 reel.py reels/01-kitchen-reel.json [--check] [--variant {a,b,all}] [--out out]` — `--check` runs validation + caption rules, prints `[PASS]`/`[FAIL]` lines like `check.py`, exits 1 on any error. Without `--check` this task may `SystemExit("assemble not implemented yet")` — later tasks fill it in.

- [ ] **Step 1: git baseline**

Run `git rev-parse --git-dir`; if it fails: `git init && git add -A && git commit -m "baseline: rahistrading carousel pipeline before reel work"` (the repo has a `.gitignore` that already expects git; if the partner declines git later, drop the remaining commit steps and keep building).

- [ ] **Step 2: Write the failing tests** in `tests/test_reel_validate.py` (path-bootstrap line first). Each case builds a minimal recipe dict (or loads the real one) and asserts the exact error substring:
  - `test_real_recipe_is_valid` — `validate_recipe(load_recipe("reels/01-kitchen-reel.json"), HERE)` → `errors == []`, `warnings` contains the no-music note (recipe ships `"music": null`).
  - `test_missing_source_file_errors` — sources.kitchen = "data/nope.mp4" → error contains `missing source file`.
  - `test_shot_out_of_range_errors` — shot `end: 999` → `shot out of range`.
  - `test_unknown_beat_shot_errors` — beat shot "ghost" → `unknown shot`.
  - `test_unknown_hook_or_endcard_errors` — variant hook "ghost" → `unknown hook`; endcard type "video" → `endcard type`.
  - `test_forbidden_figure_in_overlay_errors` — overlay ar = "1000 cfm" → `invented figure`.
  - `test_caption_word_count_errors` — `caption_en: "too short"` → `caption_en` + `words`.
  - `test_music_named_but_missing_errors` — `music: "data/music/ghost.mp3"` → `missing music file`; **and** `music: None` → errors stay empty, warning present.
  - `test_build_instagram_shape` — starts with the Arabic caption (Arabic first!), contains `DIVIDER`, `📍 Doha, Qatar`, handle, `len(...) <= IG_LIMIT`, hashtags appear exactly once each (dedupe).

- [ ] **Step 3: Run tests, confirm they fail**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL/ERROR — `ImportError: cannot import name 'load_recipe'` (module doesn't exist).

- [ ] **Step 4: Write `reels/01-kitchen-reel.json`** with the exact values pinned above (sources, 8 shots, 7 timeline beats + endcard spec, 6 overlays, 2 variants, captions, hashtags, `music: null`, `site_audio_db: -12`), and create the empty music drop zone: `mkdir -p data/music`.

- [ ] **Step 5: Implement `load_recipe`, `validate_recipe`, `build_instagram` + CLI `--check` in `reel.py`** — house style: flat functions, `err()`/`sys.exit` like `render.py`, `from check import FORBIDDEN`, `from make_pack import DIVIDER, IG_LIMIT`. Validation errors are collected (list), not raised one at a time, so `--check` prints them all.

- [ ] **Step 6: Run tests, confirm they pass**

Run: `python3 -m unittest discover -s tests -v` → all PASS.
Run: `python3 reel.py reels/01-kitchen-reel.json --check` → `[PASS] ... 0 error(s)`, exit 0. Temporarily set `"music": "data/music/x.mp3"` → FAIL with `missing music file`, revert.

- [ ] **Step 7: Commit** — `git add reel.py reels/ tests/ && git commit -m "reel: recipe schema, validation, --check"`

### Task 2: Timeline builder (variants)

**Files:**
- Modify: `reel.py` (add timeline)
- Create: `tests/test_reel_timeline.py`

**Interfaces:**
- Consumes: `load_recipe`, `validate_recipe` (Task 1).
- Produces:
  - `build_timeline(recipe: dict, variant_name: str) -> dict` returning:
    ```python
    {
      "segments": [ {"shot": str, "source": Path, "start": float, "dur": float}, ... ],
      "overlays": [ {"id": str, "ar": str, "en": str, "from": float, "dur": float}, ... ],
      "endcard": {"type": "image"|"card", "image": Path|None, "dur": 5.0},
      "total": float,          # 32.0
      "outdir_name": str,      # "01-kitchen-reel-a" / "-b"
    }
    ```
  - Segment order: hook segment first (shot from `variant["hook"]`), then the 7 shared beats in recipe order, **endcard is not a segment** (Task 4/5 build it), `total` = sum of segment durs + `endcard.dur`.
  - Overlays: recipe overlays + automatic `cta` window `from: total-5, dur: 5` **only when** `endcard.type == "image"`.
  - Raises `SystemExit("unknown variant ...")` for bad names.

- [ ] **Step 1: Write failing tests** (`tests/test_reel_timeline.py`): `test_total_is_32` (±0.01, both variants); `test_variant_a_hook_shot` (first segment shot == `hook_face`, source == kitchen file); `test_variant_b_hook_shot` (first == `hook_clean`); `test_shared_beats_identical` (segments[1:] equal for a and b); `test_cta_overlay_only_for_image_variant` (a has 7 overlays ending `from 27, dur 5`; b has 6); `test_outdir_names` (`01-kitchen-reel-a`/`-b`); `test_unknown_variant_raises`.
- [ ] **Step 2: Run, confirm fail** — `python3 -m unittest discover -s tests -v` → `ImportError: build_timeline`.
- [ ] **Step 3: Implement `build_timeline`** in `reel.py`.
- [ ] **Step 4: Run, confirm pass.**
- [ ] **Step 5: Commit** — `git commit -am "reel: timeline builder with variants"`

### Task 3: Overlay + end-card HTML rendering (Playwright, Arabic)

**Files:**
- Modify: `reel.py` (add HTML builders + Playwright render)
- Create: `tests/test_reel_render.py`

**Interfaces:**
- Consumes: `build_timeline` (Task 2).
- Produces:
  - `overlay_html(overlay: dict, width=1080, height=1920) -> str` — full document; `wrap`-style like `render.py` but with `<link href="...css2?family=IBM+Plex+Sans+Arabic:wght@400;600;700&family=Inter:wght@400;700;800...">`; root element `dir="rtl"`; bottom scrim `linear-gradient(rgba(0,0,0,0),rgba(0,0,0,.75))`; Arabic block (`ar`, 96px, 700) then English (`en`, 44px, 500, `dir="ltr"` span); red bar `#AF1A1F` above.
  - `card_html(recipe: dict, endcard: dict) -> str` — 1080×1920 ink `#1E1F21` card: `RAHIS SHEIKH TRADING` header (800 weight, letterspaced), dot-grid background (copy `DOT_GRID` idea from `render.py`), cta `ar` (76px) + `en` (40px, ltr span), footer `@rahissheikhtrading` + `📍 Doha, Qatar`.
  - `render_overlays(recipe: dict, timeline: dict, outdir: Path) -> Path` — Playwright (`sync_playwright`, chromium, viewport 1080×1920, `page.screenshot(..., omit_background=True)`, wait `document.fonts.ready`); writes `<id>.png` per overlay + `card.png` (when endcard type is card) + `overlays.json` (`[{"id","from","dur","file"}]`); returns `outdir`. Prints a warning (like `render.py`) if any overlay element overflows the viewport.

- [ ] **Step 1: Write failing tests** (`tests/test_reel_render.py`):
  - HTML unit tests (no browser): `test_font_link_includes_arabic` (`IBM+Plex+Sans+Arabic` in `overlay_html(...)`); `test_rtl_root` (`dir="rtl"`); `test_ltr_handle_span` (card html: `dir="ltr"` around the handle/📍 line); `test_arabic_text_escaped_intact` (the Arabic string appears verbatim, `"`/`&` escaped); `test_scrim_present` (`linear-gradient`).
  - Integration: `test_render_writes_pngs` — build timeline for variant `a`, call `render_overlays` into a `tempfile.TemporaryDirectory()`, assert 7 `.png` files exist, each `> 5000` bytes, plus `overlays.json` with 7 entries; for variant `b`, assert `card.png` exists and **no** 8th cta file.
- [ ] **Step 2: Run, confirm fail.**
- [ ] **Step 3: Implement** `overlay_html`, `card_html`, `render_overlays`.
- [ ] **Step 4: Run, confirm pass** + one visual spot check: `open out/... ` or view `hook.png` to confirm Arabic is shaped (not boxes), red bar + scrim present.
- [ ] **Step 5: Commit** — `git commit -am "reel: Arabic overlay + end-card rendering"`

### Task 4: Segment prep (ffmpeg normalisation + end-card segments)

**Files:**
- Modify: `reel.py` (add `prep_segments`)
- Create: `tests/test_reel_assemble.py`

**Interfaces:**
- Consumes: `build_timeline`.
- Produces:
  - `prep_segments(timeline: dict, workdir: Path, site_db: float) -> list[Path]` — for each segment, run ffmpeg producing `<workdir>/<NN>-<shot>.mp4` with **exact** filters: `-vf "fps=30,scale=1080:1920:flags=lanczos,unsharp=5:5:0.6:5:5:0.0,setsar=1"`, `-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -ar 48000 -ac 2 -b:a 128k`, video `-ss <start> -t <dur>` on input; audio: kitchen/site segments get `volume=<site_db>dB` (site audio is the only audio), written with `-af`.
  - Also prepends the **end-card segment** as the last file: `type == "card"` → loop `card.png` (`-loop 1 -t 5`); `type == "image"` → the blur-pad graph pinned in Global/env: `[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:2[bg];[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1`; both with `anullsrc=channel_layout=stereo:sample_rate=48000` as audio (`.mp4` silent track) so concat stays uniform.
  - Helper: `probe(path: Path) -> dict` — ffprobe JSON → `{width, height, fps: float, dur: float, has_audio: bool}` (used by tests and Task 6).

- [ ] **Step 1: Write failing tests.** `setUpClass` creates synthetic inputs with ffmpeg (no repo data): `testsrc2=size=480x854:rate=29.97:duration=2` + `sine=frequency=440` → `clip.mp4`; a 480×480 `color=c=orange` still → `fan.jpg`-like png. Tests:
  - `test_segment_normalised` — hand-build a one-segment timeline dict, run `prep_segments`, probe result: `width==1080`, `height==1920`, `fps==30.0` (±0.01), `has_audio`.
  - `test_segment_duration` — probe dur ≈ requested (±0.15).
  - `test_site_db_applied` — `volume=-20dB` build has lower `max_volume` than `0dB` build (ffmpeg `volumedetect` on both; assert dB difference ≈ requested ±3).
  - `test_endcard_image_segment` — endcard type image → last file exists, dur ≈ 5.0, silent-but-audio-present.
- [ ] **Step 2: Run, confirm fail** (`prep_segments` missing).
- [ ] **Step 3: Implement `prep_segments` + `probe`.**
- [ ] **Step 4: Run, confirm pass.**
- [ ] **Step 5: Commit** — `git commit -am "reel: ffmpeg segment normalisation"`

### Task 5: Final assembly + outputs

**Files:**
- Modify: `reel.py` (add `assemble`, `write_outputs`, finish CLI)

**Interfaces:**
- Consumes: `prep_segments`, `render_overlays`, `build_timeline`, `build_instagram`.
- Produces:
  - `assemble(timeline: dict, seg_paths: list[Path], overlays_dir: Path, music: Path | None, out_mp4: Path) -> Path`:
    1. concat demuxer file list, `-f concat -safe 0 -c copy` → `base.mp4`;
    2. final single encode: `[0:v]` + one `overlay=<png>:enable='between(t,<from>,<from+dur>)'` per overlay (in `overlays.json` order); audio: music present → extra input `-stream_loop -1 -i <music>`, graph `[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]`; music absent → `[0:a]loudnorm=I=-14:TP=-1.5:LRA=11[a]`; `-t <total>`; encode `libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k`.
  - `write_outputs(recipe: dict, timeline: dict, outdir: Path) -> None` — `caption_ar.txt` (ar + hashtags_ar), `caption_en.txt` (en + hashtags_en), `instagram.txt` (`build_instagram` + trailing newline), `post.json` = `{"id", "variant", "reel": "reel.mp4", "instagram", "status": "draft", "note": "Post manually in the IG app — pick a day with no carousel (strategy.md)."}`.
  - CLI completes: `--variant all` loops variants; each prints `-> out/<outdir>/reel.mp4  (32.0s)`; missing-music warning printed once.

- [ ] **Step 1: Write failing tests** (`tests/test_reel_assemble.py`, synthetic-only): build 3 fake segments (1.5s each) + a 1.5s endcard + one hand-made overlay PNG (ffmpeg `color=c=black@0.5` alpha via `format=rgba`... simplest: Playwright-rendered 1080×1920 PNG from `overlay_html` — reuse Task 3) + a sine `music.mp3`:
  - `test_assemble_output_specs` — probe `reel.mp4`: 1080×1920, fps 30, has_audio, dur ±0.2 of total (6.0).
  - `test_assemble_music_absent` — same with `music=None` → output exists, has_audio, and no exception.
  - `test_no_clipping` — `volumedetect` on output: `max_volume ≤ -0.5 dB`.
  - `test_write_outputs_shape` — real recipe + timeline → temp dir: 4 files; `instagram.txt` starts with `caption_ar` first line, `len ≤ 2200`; `post.json` parses with `status == "draft"` and `reel == "reel.mp4"`.
  - `test_cli_check_exit_codes` — subprocess `--check` on real recipe → returncode 0; on a broken copy (forbidden figure) → returncode 1.
- [ ] **Step 2: Run, confirm fail.**
- [ ] **Step 3: Implement `assemble`, `write_outputs`, CLI wiring.**
- [ ] **Step 4: Run, confirm pass** — whole suite: `python3 -m unittest discover -s tests -v`.
- [ ] **Step 5: Commit** — `git commit -am "reel: assembly, audio mix, caption outputs"`

### Task 6: Real build of both variants + README + handoff

**Files:**
- Modify: `README.md` (add reel commands under `## Commands` + a "Reel notes" short section)
- Outputs: `out/01-kitchen-reel-a/`, `out/01-kitchen-reel-b/`

This task is verification-driven (no new unit tests); each step has a checkable expected result.

- [ ] **Step 1: Validate** — `python3 reel.py reels/01-kitchen-reel.json --check` → PASS, 0 errors.
- [ ] **Step 2: Build both variants** — `python3 reel.py reels/01-kitchen-reel.json --variant all` → two dirs, each with `reel.mp4` + 4 text files; missing-music note printed.
- [ ] **Step 3: Verify specs** — for each `reel.mp4`: `ffprobe` → 1080×1920, 30/1 fps, dur 30–40s, aac audio; `ffmpeg -af ebur128 -f null -` → Integrated loudness within **−14 ±2 LU** (if outside, adjust the loudnorm pass once and note it in README); `volumedetect` → `max_volume ≤ -0.5 dB`.
- [ ] **Step 4: Visual + variant checks** — extract 1s-interval tile strips (same command pattern as used in auditing): confirm (a) Arabic overlays are shaped, RTL, inside frame, never covering the subject's face; (b) variant A's hook (0–3s) shows the worker, variant B's hook shows **no identifiable person**; (c) A's end card is the fan photo contain-centred on blur with CTA readable, B's is the ink brand card; (d) no editing-tool watermarks anywhere. View the strips with the Read tool and fix timings/copy in the recipe (±0.5s shot nudges allowed here) then rebuild.
- [ ] **Step 5: Caption sanity** — read `instagram.txt` in both dirs: Arabic first, divider, 📍 Doha, hashtags deduped, ≤ 2200 chars; one CTA.
- [ ] **Step 6: README** — add to Commands block: `python3 reel.py reels/01-kitchen-reel.json --check` / `--variant all`; notes: reels post **manually** (Buffer stays carousels), music goes in `data/music/` + recipe field, source softness at 480px accepted, variant A carries third-party Pioneer branding pending partner review.
- [ ] **Step 7: Commit** — `git add -A && git commit -m "reel: first build — two review variants + docs"`
- [ ] **Step 8: Hand to partner** — present both variants (file paths + how to view), the two review decisions (hook face / end card), and the open music item.
