"""Local reference review with optimistic concurrency and atomic persistence."""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from .data import read_jsonl, write_jsonl, sha256, resolve_crop, validate_references
from .metrics import score


def make_handler(root):
    root = Path(root).resolve()
    working = root / "data/references.local.jsonl"
    original = root / "data/references.jsonl"

    class Handler(BaseHTTPRequestHandler):
        def references(self):
            path = working if working.exists() else original
            return path, read_jsonl(path)

        def send(self, status, body, content_type="application/json"):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/":
                    return self.send(200, (Path(__file__).parent / "review.html").read_bytes(), "text/html; charset=utf-8")
                path, rows = self.references()
                if parsed.path == "/api/state":
                    runs = {}
                    for name in ["trocr-raw", "trocr-grayscale", "trocr-contrast"]:
                        p = root / "output/predictions" / f"{name}.jsonl"
                        if p.exists():
                            predictions = read_jsonl(p)
                            try:
                                report = score(rows, predictions, "pilot", True)
                            except ValueError:
                                report = None
                            runs[name] = {"predictions": {r["id"]: r for r in predictions}, "report": report}
                    return self.send(200, {"revision": sha256(path), "references": rows, "runs": runs,
                                           "manifest": json.loads((root / "data/source-manifest.json").read_text())})
                if parsed.path == "/image":
                    id = parse_qs(parsed.query).get("id", [None])[0]
                    row = next((r for r in rows if r["id"] == id), None)
                    if not row:
                        return self.send(404, {"error": "Unknown crop"})
                    return self.send(200, resolve_crop(root, row).read_bytes(), "image/png")
                if parsed.path == "/source":
                    manifest = json.loads((root / "data/source-manifest.json").read_text())
                    page = manifest["pages"][0]
                    p = (root / page["image"]).resolve()
                    if not p.is_relative_to(root) or sha256(p) != page["sha256"]:
                        raise ValueError("Source checksum mismatch")
                    return self.send(200, p.read_bytes(), "image/jpeg")
                return self.send(404, {"error": "Not found"})
            except (ValueError, OSError) as error:
                self.send(400, {"error": str(error)})

        def do_POST(self):
            if self.path != "/api/reference":
                return self.send(404, {"error": "Not found"})
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{self.headers.get('Host')}":
                return self.send(403, {"error": "Cross-origin edits are not permitted"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size <= 0 or size > 16000:
                    raise ValueError("Invalid request size")
                if not self.headers.get("Content-Type", "").startswith("application/json"):
                    raise ValueError("Expected JSON")
                update = json.loads(self.rfile.read(size))
                if not isinstance(update, dict):
                    raise ValueError("Expected a JSON object")
                path, rows = self.references()
                if update.get("revision") != sha256(path):
                    return self.send(409, {"error": "Reference changed; reload before saving"})
                row = next((r for r in rows if r["id"] == update.get("id")), None)
                if row is None:
                    raise ValueError("Unknown crop")
                text, reviewer = update.get("text"), update.get("reviewer")
                if not isinstance(text, str) or len(text) > 4000:
                    raise ValueError("Reference must be text of at most 4000 characters")
                if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 120:
                    raise ValueError("Enter reviewer attribution before saving")
                if type(update.get("reviewed")) is not bool or type(update.get("uncertain")) is not bool:
                    raise ValueError("Review and uncertainty flags must be booleans")
                if update["reviewed"] and not text.strip():
                    raise ValueError("Reviewed reference cannot be empty")
                row.update(text=text, reviewer=reviewer.strip(), reviewed=update["reviewed"], uncertain=update["uncertain"],
                           annotation_source="Reviewer-attested transcription in ledger-htr" if update["reviewed"] else "Draft reference edit in ledger-htr")
                validate_references(rows)
                temp = working.with_suffix(".jsonl.tmp")
                write_jsonl(temp, rows)
                os.replace(temp, working)
                return self.send(200, {"revision": sha256(working), "reference": row})
            except (ValueError, OSError) as error:
                return self.send(400, {"error": str(error)})

        def log_message(self, fmt, *args):
            pass

    return Handler


def serve(root, port):
    server = HTTPServer(("127.0.0.1", port), make_handler(root))
    print(f"Reference review: http://127.0.0.1:{port}", flush=True)
    server.serve_forever()
