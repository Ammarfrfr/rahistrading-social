#!/usr/bin/env python3
"""Upload a carousel's four slides to Cloudinary (unsigned preset) and record the URLs.

    python3 cloudinary_upload.py --id 06-grease-and-fire
    python3 cloudinary_upload.py --all

Reads CLOUDINARY_CLOUD_NAME / CLOUDINARY_UPLOAD_PRESET from .env.
Writes image_urls into out/<id>/post.json and the newest schedule/week-*.json.
"""
import argparse
import base64
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
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


def newest_queue():
    files = sorted((HERE / "schedule").glob("week-*.json"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def sign(params, secret):
    raw = "&".join(f"{k}={params[k]}" for k in sorted(params))
    return hashlib.sha1((raw + secret).encode()).hexdigest()


def upload(path):
    env = load()
    cloud = env.get("CLOUDINARY_CLOUD_NAME")
    api_key, secret = env.get("CLOUDINARY_API_KEY"), env.get("CLOUDINARY_API_SECRET")
    preset = env.get("CLOUDINARY_UPLOAD_PRESET")
    if not cloud:
        sys.exit("set CLOUDINARY_CLOUD_NAME in .env")

    fields = {}
    if env.get("CLOUDINARY_FOLDER"):
        fields["folder"] = env["CLOUDINARY_FOLDER"]

    if api_key and secret:                      # signed upload, preferred
        fields["timestamp"] = str(int(time.time()))
        fields["signature"] = sign(fields, secret)
        fields["api_key"] = api_key
    elif preset:                                # unsigned preset fallback
        fields["upload_preset"] = preset
    else:
        sys.exit("set CLOUDINARY_API_KEY + CLOUDINARY_API_SECRET (or a preset) in .env")

    fields["file"] = "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()
    req = urllib.request.Request(
        f"https://api.cloudinary.com/v1_1/{cloud}/image/upload",
        data=urllib.parse.urlencode(fields).encode(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r:
            payload = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"Cloudinary HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
    return payload["secure_url"], payload["public_id"]


def attach(carousel_id, urls, pids=None):
    post_file = HERE / "out" / carousel_id / "post.json"
    q = newest_queue()
    if post_file.exists():
        p = json.loads(post_file.read_text(encoding="utf-8"))
        p["image_urls"] = urls
        if pids:
            p["image_public_ids"] = pids
        post_file.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if q:
        queue = json.loads(q.read_text(encoding="utf-8"))
        for p in queue["posts"]:
            if p["id"] == carousel_id:
                p["image_urls"] = urls
                if pids:
                    p["image_public_ids"] = pids
        if pids:
            p["image_public_ids"] = pids
        q.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return q


def one(carousel_id):
    out = HERE / "out" / carousel_id
    slides = sorted(out.glob("slide*.png"), key=lambda p: int(p.stem[5:]))
    missing = [s.name for s in slides if not s.exists()]
    if missing:
        sys.exit(f"{carousel_id}: missing {', '.join(missing)}")
    urls, pids = [], []
    for s in slides:
        u, pid = upload(s)
        urls.append(u)
        pids.append(pid)
        print(f"  {s.name:12} -> {u}")
    q = attach(carousel_id, urls, pids)
    print(f"{carousel_id}: {len(urls)} urls stored" + (f" in {q.name}" if q else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if a.all:
        q = newest_queue()
        if not q:
            sys.exit("no queue; run make_pack.py first")
        for p in json.loads(q.read_text(encoding="utf-8"))["posts"]:
            if not p.get("image_urls"):
                print(p["id"])
                one(p["id"])
    elif a.id:
        one(a.id)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
