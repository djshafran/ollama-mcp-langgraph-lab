from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import urllib.parse


def _guess_root(tokens: list[str]) -> int:
    for i, tok in enumerate(tokens):
        t = tok.strip()
        if any(v in t for v in ("ति", "ते", "न्ति", "गच्छति", "ददाति", "करोति")):
            return i
    return max(len(tokens) - 1, 0)


def _guess_role(token: str) -> str:
    t = token.strip()
    if "कर्मण" in t or "फलेषु" in t or t.endswith("े") or t.endswith("षु") or t.endswith("णि"):
        return "adhikaraṇa"
    if t.endswith("ः") or t.endswith("स्"):
        return "kartṛ"
    if t.endswith("ं") or t.endswith("म्"):
        return "karman"
    return "dep"


def _build_dependencies(text: str) -> list[dict]:
    tokens = [tok for tok in text.split() if tok]
    if not tokens:
        return []
    root = _guess_root(tokens)
    deps = [{"head": None, "dep": root + 1, "role": "root"}]
    for i, tok in enumerate(tokens):
        if i == root:
            continue
        deps.append({"head": root + 1, "dep": i + 1, "role": _guess_role(tok)})
    return deps


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/parse":
            self.send_response(404)
            self.end_headers()
            return
        params = urllib.parse.parse_qs(parsed.query)
        text = (params.get("text") or [""])[0]
        payload = {"dependencies": _build_dependencies(text)}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/parse":
            self.send_response(404)
            self.end_headers()
            return
        size = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(size).decode("utf-8", errors="replace")
        params = urllib.parse.parse_qs(data)
        text = (params.get("text") or [""])[0]
        payload = {"dependencies": _build_dependencies(text)}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


def main():
    server = HTTPServer(("0.0.0.0", 8080), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()

