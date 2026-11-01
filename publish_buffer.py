#!/usr/bin/env python3
"""Push a week-*.json queue into Buffer (Instagram + Facebook).

Needs, in .env: BUFFER_API_KEY, BUFFER_CHANNEL_INSTAGRAM, BUFFER_CHANNEL_FACEBOOK.
Needs, in each post: image_urls — 4 public HTTPS URLs (Buffer fetches them at publish
time; there is no upload endpoint).

    python3 publish_buffer.py --check            # channels + queue, no writes
    python3 publish_buffer.py --live             # actually schedule
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from buffer_api import post
from envload import load

HERE = Path(__file__).resolve().parent
MUTATION = """
mutation {{
  createPost(input: {{
    text: {text},
    channelId: "{channel}",
    schedulingType: automatic,
    mode: customScheduled,
    dueAt: "{due}"
    {assets}{meta}
  }}) {{
    ... on PostActionSuccess {{ post {{ id text }} }}
    ... on MutationError {{ message }}
  }}
}}
"""


def utc_z(iso):
    return datetime.fromisoformat(iso).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def assets(urls):
    if not urls:
        return ""
    body = ", ".join('{ image: { url: "%s" } }' % u for u in urls)
    return f",\n    assets: [{body}]"


def meta(service):
    return ("\n    metadata: { instagram: { type: post, shouldShareToFeed: true } }"
            if service == "instagram" else
            "\n    metadata: { facebook: { type: post } }")


def create(channel, text, due, urls, service):
    q = MUTATION.format(text=json.dumps(text, ensure_ascii=False), channel=channel,
                        due=utc_z(due), assets=assets(urls), meta=meta(service))
    res = post(q)
    if "errors" in res:
        return None, res["errors"][0].get("message", "graphql error")
    payload = res.get("data", {}).get("createPost", {})
    if "message" in payload:
        return None, payload["message"]
    return payload.get("post", {}).get("id"), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", default=None, help="path to week-*.json (default: newest)")
    ap.add_argument("--check", action="store_true", help="validate only (default)")
    ap.add_argument("--live", action="store_true", help="really create the posts")
    a = ap.parse_args()

    env = load()
    for k in ("BUFFER_API_KEY", "BUFFER_CHANNEL_INSTAGRAM", "BUFFER_CHANNEL_FACEBOOK"):
        if not env.get(k):
            sys.exit(f"{k} missing in .env")

    path = Path(a.week) if a.week else max((HERE / "schedule").glob("week-*.json"),
                                          key=lambda p: p.stat().st_mtime, default=None)
    if not path:
        sys.exit("no schedule/week-*.json — run make_pack.py first")
    queue = json.loads(Path(path).read_text(encoding="utf-8"))

    channels = {"instagram": env["BUFFER_CHANNEL_INSTAGRAM"],
                "facebook": env["BUFFER_CHANNEL_FACEBOOK"]}
    todo = [p for p in queue["posts"] if p.get("status") in ("draft", "failed")]
    print(f"{path.name}: {len(todo)} post(s) to schedule, {len(queue['posts']) - len(todo)} already done\n")

    blocked = [p["id"] for p in todo if not p.get("image_urls")]
    if blocked:
        print("NOT READY — these posts have no public image URLs:")
        for i in blocked:
            print("  -", i)
        print("\nBuffer has no upload endpoint; host the four PNGs and add `image_urls` to the")
        print("queue. See docs/automation-setup.md. Nothing was sent.")
        if a.live:
            sys.exit(1)

    for p in todo:
        ok = True
        for service, key in (("instagram", "instagram"), ("facebook", "facebook")):
            if not a.live:
                print(f"  would schedule {p['due_at'][:16]}  {service:9}  {p['id']}")
                continue
            pid, err = create(channels[service], p[key], p["due_at"], p["image_urls"], service)
            if err:
                print(f"  FAILED   {service:9}  {p['id']}: {err}")
                p["status"] = "failed"
                p["error"] = err
                ok = False
            else:
                print(f"  queued   {service:9}  {p['id']}  (buffer id {pid})")
                p.setdefault("buffer_ids", {})[service] = pid
        if a.live and ok:
            p["status"] = "scheduled"
            p.pop("error", None)

    if a.live:
        path.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nupdated {path.name}")
    else:
        print("\ndry run — nothing sent. add --live to schedule.")


if __name__ == "__main__":
    main()
