# Social publishing — Buffer path (no Meta developer app)

Two separate accounts (one Instagram, one Facebook) stay separate. Buffer connects each one
directly, so no Facebook Page link, no Meta app, no App Review, no token rotation.

Current setup: Instagram is a **Creator** account, both platforms get **Arabic + English**,
**five posts a week** (Sunday–Thursday, 18:00 Doha).

```
carousels/*.json -> render.py -> out/<id>/slide1-4.png
                                        |
                          make_pack.py  -> out/<id>/instagram.txt
                                           out/<id>/facebook.txt
                                           out/<id>/post.json
                                        |
                          schedule/week-YYYY-WW.json  (5 dated posts)
                                        |
                     Buffer queue (drag-drop now, API later)
```

## One-time, on your side

1. Create a free Buffer account — <https://buffer.com>. Free plan: 3 channels, 10 queued
   posts per channel, API access included.
2. **Channels → Connect → Instagram → Professional → Connect to Instagram.** Sign in with the
   Instagram account. No Facebook Page involved.
3. **Channels → Connect → Facebook →** choose the Page. Separate connection.
4. Nothing else. No developer portal, no tokens, no App Review.

## Weekly, on my side

```bash
python3 check.py                 # copy + fact rules
python3 measure.py               # no overlaps
python3 make_pack.py             # per-platform captions + the week's queue
```

`make_pack.py` writes, for every carousel:

| File | Contents |
| --- | --- |
| `instagram.txt` | English caption, Arabic caption, all 19 hashtags (≤2200 chars) |
| `facebook.txt` | same two captions, 5 hashtags |
| `post.json` | id, due date/time, slide paths, both captions, status |

and one queue file: `schedule/week-YYYY-WW.json`, five posts dated Sunday–Thursday at 18:00
Asia/Qatar. Change `POST_HOUR` / `CADENCE` in `make_pack.py` to move them.

## Two ways to get the queue into Buffer

### A. Drag-drop — zero setup

Per post, about two minutes: open `out/<id>/`, drag `slide1-4.png` into Buffer, paste
`instagram.txt`, set the time, repeat for Facebook with `facebook.txt`. Five posts ≈ 15
minutes a week. Nothing can expire or break.

### B. Fully automatic — needs public image URLs

Buffer's API has **no upload endpoint**. `createPost` takes `assets: [{ image: { url } }]`
and fetches that URL when the post publishes, so the images must live at a stable public
HTTPS URL. Cloudinary's free tier is the least fiddly host (Buffer recommends it):

1. Create a free Cloudinary account, note the **cloud name**.
2. Settings → Upload → Add upload preset → **Signing mode: Unsigned**. Note the preset name.
3. Send me those two names (they are not secrets).
4. Paste them into `.env` as `CLOUDINARY_CLOUD_NAME` and `CLOUDINARY_UPLOAD_PRESET`, then
   run `python3 cloudinary_upload.py --all`.

## Review page

```bash
python3 studio.py     # http://127.0.0.1:8765, localhost only
```

Shows every post in the current queue with its four slides, editable Instagram and Facebook
captions (with character counters), and three actions: **Save**, **Upload slides**,
**Schedule in Buffer**. Scheduling is blocked until that post's images are hosted and until
Buffer is connected. The page writes straight back to `schedule/week-*.json`.

Nothing else changes; the captions and dates are already built. Any host works as long as the
URL is public, direct, HTTPS and does not expire before the post publishes.

## Connected accounts (verified via API)

| Service | Buffer channel id | Name |
| --- | --- | --- |
| Instagram | `6adc6d28778b240e2fabf6bc` | `rahissheikhtrading` |
| Facebook | `6adc6e05778b240e2fabfc3e` | `Rahis Sheikh trading` |

Organization `6adc6cad73a6eff0daf41e0b` ("My organization"). These ids are in `.env` too; only
the API key is secret. `.env` is `chmod 600` and listed in `.gitignore`. Check it with
`python3 envload.py` — it prints lengths, never values.

## Image cleanup

Cloudinary keeps every upload forever by default. `cleanup_cloudinary.py` deletes each
carousel's images **three days after the post publishes** — not after upload, because Buffer
fetches the images at publish time and early deletion silently breaks the post.

```bash
python3 cleanup_cloudinary.py            # dry run
python3 cleanup_cloudinary.py --live     # delete
python3 cleanup_cloudinary.py --days 2 --live
```

Run it at the start of each weekly session. A macOS `launchd` job can run it daily if you
want it fully hands-off; it only fires while the machine is awake.

## Weekly loop

1. You run me once a week.
2. I read the Buffer queue / sent posts, report what went out and what did not.
3. I render and verify the next five, then regenerate `schedule/week-*.json`.
4. Posts publish from Buffer at the set times.

## Limits / gotchas

- Buffer free allows **10 queued posts per channel**. Five a week is fine; do not queue two
  weeks ahead or the oldest slot is refused.
- Instagram Creator accounts auto-publish through Buffer's Instagram-login connection.
  Personal accounts would only get a phone reminder.
- Carousel images: 4:5 to 1.91:1, JPEG. Slides are 1080×1350 = 4:5, so they pass unchanged.
- Buffer needs the carousel as 2–10 images; the batch is 4.
- Brand/handle is confirmed: both accounts are `@rahissheikhtrading`, matching the slides.
  The Instagram display name still reads "Rahis Kitchen Equipments" — align it to the Page
  using `profile/README.md`.


review page
cd ~/Project_shit/rahistrading-social
python3 studio.py

