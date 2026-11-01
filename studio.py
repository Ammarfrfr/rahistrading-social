#!/usr/bin/env python3
"""Local review page: see the week, edit captions, upload slides, schedule.

    python3 studio.py          ->  http://127.0.0.1:8765

Bound to localhost only. Never expose it: it can schedule posts.
"""
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cloudinary_upload import attach, newest_queue, one as upload_one
from envload import load
from publish_buffer import create

HERE = Path(__file__).resolve().parent
PORT = 8765


def read_queue():
    q = newest_queue()
    if not q:
        sys.exit("no schedule/week-*.json — run make_pack.py")
    data = json.loads(q.read_text(encoding="utf-8"))
    return q, data


def write_queue(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path == "/":
            self._send(200, (HERE / "studio.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/state":
            _, q = read_queue()
            env = load()
            self._send(200, {
                "week": q["week"],
                "buffer": bool(env.get("BUFFER_API_KEY")),
                "cloudinary": bool(env.get("CLOUDINARY_CLOUD_NAME") and env.get("CLOUDINARY_UPLOAD_PRESET")),
                "posts": q["posts"],
            })
        elif self.path.startswith("/out/"):
            p = (HERE / self.path.lstrip("/")).resolve()
            if HERE not in p.parents or not p.exists():
                return self._send(404, {"error": "not found"})
            self._send(200, p.read_bytes(), "image/png")
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            if self.path == "/api/save":
                body = self._body()
                qp, q = read_queue()
                for p in q["posts"]:
                    if p["id"] == body["id"]:
                        p["instagram"] = body["instagram"]
                        p["facebook"] = body["facebook"]
                        p["status"] = "reviewed" if p["status"] == "draft" else p["status"]
                        post_file = HERE / "out" / p["id"] / "post.json"
                        if post_file.exists():
                            pp = json.loads(post_file.read_text(encoding="utf-8"))
                            pp.update(instagram=p["instagram"], facebook=p["facebook"], status=p["status"])
                            post_file.write_text(json.dumps(pp, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
                write_queue(qp, q)
                return self._send(200, {"ok": True})

            if self.path == "/api/upload":
                body = self._body()
                upload_one(body["id"])
                return self._send(200, {"ok": True})

            if self.path == "/api/schedule":
                body = self._body()
                qp, q = read_queue()
                env = load()
                post = next(p for p in q["posts"] if p["id"] == body["id"])
                if not post.get("image_urls"):
                    return self._send(400, {"error": "upload the slides first"})
                if post.get("status") == "scheduled":
                    return self._send(400, {"error": "already scheduled"})
                done = {}
                for service in ("instagram", "facebook"):
                    pid, err = create(env["BUFFER_CHANNEL_" + service.upper()],
                                      post[service], post["due_at"], post["image_urls"])
                    if err:
                        return self._send(400, {"error": f"{service}: {err}"})
                    done[service] = pid
                post["status"] = "scheduled"
                post["buffer_ids"] = done
                write_queue(qp, q)
                return self._send(200, {"ok": True, "ids": done})

            self._send(404, {"error": "not found"})
        except Exception as e:  # noqa: BLE001 - surfaced to the page
            self._send(500, {"error": str(e)})


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}"
    print(f"studio on {url}  (ctrl-c to stop)")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
