#!/usr/bin/env python3
"""Read .env without a dependency, and report which keys are set — never the values.

    python3 envload.py
"""
import sys
from pathlib import Path

ENV = Path(__file__).resolve().with_name(".env")
KEYS = ["BUFFER_API_KEY", "BUFFER_ORG_ID", "BUFFER_CHANNEL_INSTAGRAM", "BUFFER_CHANNEL_FACEBOOK"]


def load(path=ENV):
    out = {}
    if not Path(path).exists():
        return out
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main():
    env = load()
    missing = 0
    for k in KEYS:
        v = env.get(k, "")
        if v:
            print(f"  {k:26} set ({len(v)} chars)")
        else:
            print(f"  {k:26} MISSING")
            missing += 1
    if missing:
        print(f"\n{missing} key(s) still empty — edit {ENV}")
        sys.exit(1)
    print("\nall keys present")


if __name__ == "__main__":
    main()
