# Strategy — what we post, when, and how we learn

## Timing (Doha, UTC+3)

GCC research consistently puts attention at **11:00–13:00** (lunch, decision-makers on
phones) and **19:00–21:00** (evening scroll). Weekdays outperform weekends for B2B.

Slots used by `make_pack.py` (`TIMES` dict, edit there):

| Day | Time | Why |
| --- | --- | --- |
| Mon | 12:30 | start of the work week, lunch check-in |
| Tue | 19:30 | evening browsing, highest general engagement |
| Wed | 12:30 | midweek lunch peak |
| Thu | 19:30 | last workday, evening |
| Fri | 12:30 | weekend scroll, lighter feed |

First post of this run goes out **tonight 19:30** because the 12:30 slot has passed.

## Location

Every caption now carries `📍 Doha, Qatar` above the hashtags, on both platforms.
Native location tagging is a per-post picker; Buffer's API does not expose a stable
location id, so the text line is the reliable route. If you want the blue location pin too,
set it once per post in Buffer's composer (it takes two clicks).

## Weekly loop

1. **Read** — pull last week's posts and their numbers (reach, likes, saves, comments, DMs,
   calls). Save the raw pull in `data/`.
2. **Judge** — for each post: did it earn saves or messages, or just likes? Saves and DMs are
   the real signal for a supplier; likes are vanity here.
3. **Write down** — append to `data/strategy.md` under *Learnings*: what worked, what did
   not, what to avoid. One line each, no essays.
4. **Adjust** — change one variable per week only: time slot, hook style, image choice, or
   caption length. Never all four at once, or nothing is measurable.
5. **Build** — next five carousels follow the current rules; anything that failed gets cut.
6. **Ship** — regenerate the queue, upload, schedule.

## Current rules (v1)

- Hook slide = one specific claim, never a generic "quality matters" line.
- Photo-led and type-led posts alternate, so the grid does not read as a wall of text.
- Captions: Arabic first for local trust, English second, then hashtags. One CTA only.
- No invented figures. No stock photos. Client photos only.
- Contact slide carries one clear action: call or WhatsApp.

## Weekly formats

- **Monday to Thursday** — standard four-page carousel: hook, two info pages, contact.
- **Friday** — tier list, seven pages: hook → F → A → B → C → S → contact. Built with the
  `tier` slide type in `render.py` (coloured letter block, claim, one paragraph, tier ladder).
  Never skip the F page; the bad answer is what makes the good ones land.
- The tier ladder always shows S A B C D E F with only the used tiers filled.

## Learnings

_Empty until the first week of data lands. Updated every Monday._

## Avoid

- Posting twice in one day (splits reach, annoys followers).
- Repeating the same hook formula more than twice in a row.
- Selling in the first line. The first line earns the second.
- Chasing likes instead of saves and messages.
- Changing the brand handle or display name mid-campaign.

## Metrics that matter

| Metric | Why |
| --- | --- |
| Saves | someone intends to act later |
| DMs / calls | direct pipeline |
| Profile visits | people checking legitimacy |
| Reach (non-followers) | whether hashtags and timing work |
| Likes | weakest signal, track but do not optimise for it |
