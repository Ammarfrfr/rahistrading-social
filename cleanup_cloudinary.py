#!/usr/bin/env python3
"""Delete carousel images from Cloudinary once the post has been live a few days.

TTL is measured from the post's publish time (due_at), never from the upload time:
Buffer fetches the images when the post publishes, so early deletion would break it.

    python3 cleanup_cloudinary.py            # dry run
    python3 cleanup_cloudinary.py --live     # delete
    python3 cleanup_cloudinary.py --days 3 --live
"""
import argparse
import base64
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from envload import load

HERE = Path(__file__).resolve().parent
try:
    import certifi
    import ssl
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    import ssl
    SSL_CTX = ssl.create_default_context()


def public_id(url):
    """https://res.cloudinary.com/<cloud>/image/upload/v123/<folder>/<id>.png -> folder/id"""
    tail = url.split("/upload/", 1)[-1]
    if tail.startswith("v") and "/" in tail:
        tail = tail.split("/", 1)[1]
    return tail.rsplit(".", 1)[0]


def queues():
    return sorted((HERE / "schedule").glob("week-*.json"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=3.0, help="grace period after publish")
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()

    env = load()
    cloud = env.get("CLOUDINARY_CLOUD_NAME")
    key, secret = env.get("CLOUDINARY_API_KEY"), env.get("CLOUDINARY_API_SECRET")
    if not (cloud and key and secret):
        sys.exit("Cloudinary cloud name / key / secret missing in .env")

    cutoff = datetime.now(timezone.utc) - timedelta(days=a.days)
    due, targets = [], []
    for qp in queues():
        q = json.loads(qp.read_text(encoding="utf-8"))
        for p in q["posts"]:
            if p.get("cleaned_at") or not p.get("image_urls"):
                continue
            published = datetime.fromisoformat(p["due_at"])
            if published > cutoff:
                continue
            ids = p.get("image_public_ids") or [public_id(u) for u in p["image_urls"]]
            due.append((qp, p, ids))
            targets += ids

    if not due:
        print("nothing old enough to clean (grace %.1f days after publish)" % a.days)
        return

    print(f"{len(due)} post(s), {len(targets)} image(s) past the {a.days:g}-day grace:")
    for qp, p, ids in due:
        print(f"  {p['due_at'][:10]}  {p['id']:32} {len(ids)} images")
    if not a.live:
        print("\ndry run — add --live to delete")
        return

    auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
    for start in range(0, len(targets), 100):
        batch = targets[start:start + 100]
        qs = urllib.parse.urlencode([("public_ids[]", i) for i in batch])
        req = urllib.request.Request(
            f"https://api.cloudinary.com/v1_1/{cloud}/resources/image/upload?{qs}",
            method="DELETE",
            headers={"Authorization": "Basic " + auth},
        )
        try:
            with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as r:
                res = json.loads(r.read())
        except urllib.error.HTTPError as e:
            sys.exit(f"delete failed {e.code}: {e.read().decode(errors='replace')[:300]}")
        print("deleted:", len(res.get("deleted", {})), "partial:", len(res.get("partial", {})))

    now = datetime.now(timezone.utc).isoformat()
    for qp, p, ids in due:
        q = json.loads(qp.read_text(encoding="utf-8"))
        for post in q["posts"]:
            if post["id"] == p["id"]:
                post["cleaned_at"] = now
        qp.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("queues marked cleaned")


if __name__ == "__main__":
    main()
