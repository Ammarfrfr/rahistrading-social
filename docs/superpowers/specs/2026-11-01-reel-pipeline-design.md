# Reel pipeline (`reel.py`) — design

Date: 2026-11-01
Status: questions answered — handover awaiting partner approval of this document
Chosen approach: **option 1 — a reel pipeline in this repo** (decided in conversation, 2026-11-01)
Builder check: run twice (DeepSeek V4 Pro, then DeepSeek V4.1 Flash **max** at partner's request); questions sorted below.

## Intent

Turn the client's raw WhatsApp clips into a public Instagram Reel for
@rahissheikhtrading, aimed at a Qatari (Doha) audience who watch on their feed and
then ask questions in the comments/DMs. Today the repo can only build carousels
(`render.py` → PNGs → captions); video has no tooling at all. This adds a second,
equally repeatable format: next week's reel should be one command, not one evening
in CapCut.

The reel's job is not to sell — it matches `data/strategy.md`: earn **questions, DMs
and saves**, never likes alone. The last frame must invite a question.

## Source material (audited 2026-11-01, in `data/`)

| File | Length | Verdict |
|---|---|---|
| `WhatsApp Video 2026-10-26 at 19.08.47.mp4` | 30s, 480×854 | **Primary.** Completed kitchen: counters + dough sheeter (0–4s), hood/range row with worker (5–11s), baffle-filter close-ups (11–17s), pots on range (17–21s), weak wall-hood/pallet angles (21–30s). Real audio, peaks −1 dB. |
| `WhatsApp Video 2026-10-27 at 23.09.47.mp4` | 25s, 478×850, ~29.83fps | **Support.** Install in progress: floor junk 0–1s (cut), dark ceiling ducts (1–8s), hood panels + duct run (8–13s), ladder/work light (13–17s), workers fitting panels (17–23s), tail (23–25s). |
| `WhatsApp Video 2026-10-26 at 19.08.43.mp4` | 2s, 480×854 | **Excluded.** Floor/door pan, unusable. |
| `WhatsApp Image 2026-10-26 at 19.08.53.jpeg` | 974×1239 | Centrifugal fan shot with a prominent third-party **Pioneer** sticker, spec nameplate and a watermark — rendered **as an end-card variant for review** (README's image rule normally excludes other companies' names/watermarks; partner is reviewing it deliberately). |

Both usable clips are WhatsApp-compressed 480px portrait — soft when scaled.
Narrative built into the footage: **site → install → finished kitchen**.
Identifiable workers appear in the proposed hook and work beats — partner chose to
**see both versions** (faces visible and faces cut around) and review.

## Goals

1. `reel.py` + a JSON recipe format, mirroring `render.py` + `carousels/*.json`, so a
   new reel is a data change, not a code change.
2. Correct Arabic on screen. ffmpeg `drawtext` mangles Arabic shaping/bidi, so text
   is rendered to transparent PNGs by the repo's Playwright/HTML path, then
   composited by ffmpeg. **Correction from builder check:** the repo has *no* Arabic
   rendering today — slides are English-only, `render.py` loads Inter (Latin-only),
   and Arabic exists only inside plain caption files. So this goal *adds* one: a
   bundled Arabic webfont plus `dir="rtl"` handling in the overlay HTML, with mixed
   bidi lines tested (Arabic + Latin `@rahissheikhtrading` + 📍 Doha).
3. A 30–40s output at 1080×1920 / 30fps (portrait, feed-ready), loudness-normalised
   to roughly −14 LUFS with the supplied music bed and the original worksite audio
   mixed per the Audio decision below.
4. `out/<reel-id>/` ships `reel.mp4`, `instagram.txt` (combined bilingual, paste-ready),
   `caption_ar.txt`, `caption_en.txt` and `post.json` — shaped like a carousel's
   output folder, minus anything the video flow can't honestly provide.
5. Recipe validation up front: missing sources, out-of-range in/out points, missing
   music file → fail loudly before any encoding (the `check.py` philosophy).

## Non-goals and anti-goals

- **No automatic publishing.** Reels post manually in the IG app (location tag is a
  picker, music choice is per-post). Buffer stays for carousels.
- **No integration into the carousel scheduling machinery.** `make_pack.py`,
  `studio.py`, `schedule/week-*.json` and `cloudinary_upload.py` are untouched —
  that helper is image-only (`image/upload`), and teaching it video, plus extending
  the queue schema and review UI to a second content type, is deliberately not this
  project's scope. The reel's `post.json` is a **local manifest for the human**
  (combined caption, file path, suggested slot note), not a scheduler input.
- **No colour grading suite, no voiceover/TTS, no auto-transcription.** Sources are
  what they are; polish is trimming + framing + type.
- **No invented claims** — same rule as `check.py`: no figures (cfm, kW, %) that the
  client never supplied. The reel persuades with footage, not numbers.
- **No editing-tool watermarks** anywhere in the export.
- **No in-app trending music** baked or added later on the business account —
  licensing risk (see Music). This is an explicit anti-goal, not an omission.
- **No informative/explainer video in this pass.** The partner flagged a future
  "educational ducting" video (explaining the work, not just showing it). Deliberately
  deferred: it needs a script/voiceover/narration workflow that doesn't exist here.
  Building this pipeline first is what makes that video cheap later.

## Constraints

- Sources are fixed and low resolution; upscaled output will be soft. Mitigation:
  favour tighter shots over wide pans, `lanczos` upscale + light `unsharp`, accept
  phone-shot authenticity rather than fight it.
- v3 is ~29.83fps and has non-monotonic DTS warnings → every segment goes through a
  normalising filter chain (fps=30, CFR, re-encode per segment) before concat.
- Arabic text must come from the HTML renderer, never ffmpeg.
- Music must be commercially cleared (below); the pipeline treats it as user-supplied.
- Keep the repo's tone: small single-purpose scripts, JSON as data, no framework.

## Approaches considered

1. **Repo pipeline (chosen).** `reel.py` + recipes, Playwright-rendered overlays,
   ffmpeg assembly. Repeatable, correct Arabic, builds on what exists. Cost: slower
   first build; no in-app trending audio.
2. **Edit kit for CapCut.** I produce EDL/script/captions, partner assembles on the
   phone. Fastest to a first result and gets trending audio, but manual every time
   and never automates. Rejected in favour of repeatability.
3. **Agent video tool (OpenMontage / HyperFrames).** Built for LLM-generated video
   from scratch, not trimming two clips; needs API plumbing and would render Arabic
   worse than the pipeline already here. Rejected as heavier and worse for this job.

## Music (decision: user-supplied, pipeline mixes it)

Research (2026-07/10 sources): Instagram's licensed library is **personal,
non-commercial use only**; business accounts like @rahissheikhtrading get a restricted
library, and using unlicensed tracks on a brand post risks muted audio or strikes.
Safe routes, in order:

1. **Meta Sound Collection** — free, 14k+ tracks, explicitly cleared for commercial
   use incl. ads, downloaded from Meta Business Manager. Best default.
2. **Pixabay Music** — free, commercial use, no attribution; save the license page
   per track (some tracks can still trip Content ID — keep the receipt).
3. **Licensed/paid library** (Artlist, Epidemic, Soundstripe) if the partner already
   subscribes.

Workflow: partner drops the chosen file into `data/music/` and names it in the
recipe. **No track yet?** The reel still builds with original worksite audio only and
`reel.py` prints a note saying so — the pipeline never blocks on music.

### Audio mix (builder's call — flags the earlier contradiction)

The first draft contradicted itself on which layer leads. Resolved: **the music bed
is the primary/foreground layer**; the original worksite audio stays audible
underneath as texture at a fixed reduced level (default ≈ −12 dB relative to source,
recipe-overridable; optional sidechain ducking is an implementation detail). One
`loudnorm` pass on the final at ≈ −14 LUFS. Rationale: music carries pacing and
holds the watch-through; site sound keeps the authenticity. Flip in the recipe if
the partner wants site-forward instead.

## Reel structure (proposed — final in/out points land in the plan)

Story: *site → install → finished kitchen*, Arabic-first on-screen copy.
Hook/work-beat shots currently show worker faces — subject to the consent answer.

| Beat | ~Time | Source | On-screen text (Arabic big, English small) |
|---|---|---|---|
| Hook | 0:00–0:03 | v2 5–9s (hood + range row) | Hook claim — one specific line, never "quality matters" |
| Before/site | 0:03–0:09 | v3 1.5–6s (dark ceiling ducts) | «قبل» context line |
| The work | 0:09–0:15 | v3 17–23s (workers fitting panels) | Install line |
| Detail | 0:15–0:20 | v2 11–15s (baffle filters close-up) | Craft line |
| Payoff | 0:20–0:31 | v2 15–21s + 0–4s (range, counters, sheeter) | Finished-kitchen line |
| Question card | 0:31–0:38 | End card — **both variants built** (fan photo / HTML brand card) | Question CTA + `@rahissheikhtrading` + 📍 Doha |

The card carries the QA prompt — e.g. an Arabic question inviting comments/DMs about
their own kitchen's ventilation — one CTA only, per `strategy.md`.

### Captions

The combined `instagram.txt` is written by `reel.py` itself (Arabic body + English
body + `📍 Doha` + deduped hashtags) so `make_pack.py` stays carousel-only. Reel
captions follow the same house rules as carousel captions: Arabic first, English
second, one CTA, no invented figures, same hashtag discipline — and `reel.py` runs
the same limits/fact checks (`check.py`-style) over its caption output before
reporting success.

### Scheduling

Not part of the pipeline. Posting is manual; the partner picks the day, respecting
`strategy.md`'s never-post-twice-in-one-day rule (a reel day = no carousel that day,
or it replaces one).

## Decisions already made (with reason)

- **Format** — 1080×1920, 30fps, 30–40s: IG Reel specs, short enough to hold the
  average watch, long enough for the full story.
- **Audio** — music primary, worksite texture beneath, `loudnorm` ≈ −14 LUFS final
  (see Audio mix).
- **Text rendering** — HTML/Playwright → transparent PNG → ffmpeg overlay, with a
  *new* Arabic webfont layer (repo has no Arabic rendering today). Chosen because
  Arabic shaping is not solved by ffmpeg `drawtext`.
- **Arabic typeface** — IBM Plex Sans Arabic paired with the existing Inter;
  builder's call, flagged for approval, trivial to swap before delivery.
- **Output layout** — `out/<reel-id>/`, same convention as carousels, so the weekly
  rhythm stays familiar; `post.json` is a local human manifest only.
- **Standalone** — no changes to `make_pack.py`, `studio.py`, `schedule/` or
  Cloudinary/Buffer flows.
- **Publishing** — manual in-app for v1 (location picker + per-post audio choice).
- **Language** — Arabic first, English second, matching every caption in the repo.
- **Quality bar** — dead frames and the 2s clip are cut, not salvaged; softness is
  accepted and framed around.

## Preview variants (answered 2026-11-01: build both, partner reviews)

Both open questions were answered the same way — **build both, I'll review**. So the
first delivery produces preview builds, not one final file:

1. **Hook variant A** — faces visible (v2 5–9s, worker in frame).
   **Hook variant B** — faces avoided: same beat built from face-free frames/shots
   (e.g. the counters/sheeter open or filter close-ups) so no identifiable person
   leads the reel. No blur step unless review asks for one.
2. **End card variant A** — fan photo as delivered (Pioneer sticker, nameplate,
   watermark intact).
   **End card variant B** — clean dark brand card rendered in HTML, matching the
   carousel style (handle + 📍 Doha + question CTA).

Practical shape: two preview reels — combo 1 (hook A + card A) and combo 2 (hook B +
card B) — each in its own `out/<reel-id>/`. The choices are **mix-and-match**: hook
and card are independent recipe fields, so any "I want hook A with card B" outcome is
a one-field edit and a re-render, never a rebuild. Pipeline therefore needs *both*
end-card modes (image and HTML card) regardless of the review outcome.

The pipeline also learns a small `--variant` / per-variant shot override from this,
which stays useful for any future A/B habit.

## What's left to the builder

- The exact EDL (frame-accurate in/out per shot) and text beat timings — tuned by
  eye against the footage, then written into the recipe.
- The Arabic hook + card copy, drafted to `strategy.md` rules (one specific claim,
  no figures, no selling in line one) for the partner to approve.
- Filter chain specifics (scale/unsharp values, concat approach, ducking method)
  chosen during implementation.
- Recipe schema field names, mirroring the carousel JSON style.
- Arabic overlay rendering (webfont + `dir="rtl"` + bidi test) implemented and
  visually verified per goal 2.
