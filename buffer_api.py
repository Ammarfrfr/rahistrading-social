#!/usr/bin/env python3
"""Minimal Buffer API client. Reads BUFFER_API_KEY from .env — never logs it.

    python3 buffer_api.py --orgs
    python3 buffer_api.py --channels <organizationId>
"""
import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request

from envload import load

ENDPOINT = "https://api.buffer.com"

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # system python usually has working roots
    SSL_CTX = ssl.create_default_context()


def post(query, variables=None):
    key = load().get("BUFFER_API_KEY")
    if not key:
        sys.exit("BUFFER_API_KEY is empty — fill .env")
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        sys.exit(f"HTTP {e.code}: {detail}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orgs", action="store_true")
    ap.add_argument("--channels", metavar="ORG_ID")
    a = ap.parse_args()

    if a.orgs:
        data = post("{ organizations { id name } }")
        print(json.dumps(data, indent=2))
    elif a.channels:
        data = post(
            "query($org: String!) { channels(input: { organizationId: $org }) "
            "{ id name displayName service isQueuePaused } }",
            {"org": a.channels},
        )
        print(json.dumps(data, indent=2))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
