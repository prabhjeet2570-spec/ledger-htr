import hashlib
import json
from pathlib import Path


def read_jsonl(path):
    records = []
    ids = set()
    for number, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row.get("id"), str) or not row["id"]:
            raise ValueError(f"Missing id at line {number}")
        if row["id"] in ids:
            raise ValueError(f"Duplicate id: {row['id']}")
        ids.add(row["id"])
        records.append(row)
    return records


def write_jsonl(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_references(rows):
    pages = {}
    for row in rows:
        page, split = row.get("page_id"), row.get("split")
        if not isinstance(page, str) or not page or split not in {"pilot", "dev", "test"}:
            raise ValueError(f"Invalid page or split for {row['id']}")
        if page in pages and pages[page] != split:
            raise ValueError(f"Page leakage: {page} appears in multiple splits")
        pages[page] = split
        if not isinstance(row.get("text"), str):
            raise ValueError(f"Reference text must be a string: {row['id']}")
        if not isinstance(row.get("reviewed"), bool):
            raise ValueError(f"Reference needs an explicit reviewed boolean: {row['id']}")
        if row["reviewed"] and not row.get("reviewer"):
            raise ValueError(f"Reviewed reference needs reviewer attribution: {row['id']}")
        if row.get("kind") not in {"text", "name", "date", "amount"}:
            raise ValueError(f"Invalid crop kind: {row['id']}")


def resolve_crop(root, record):
    root = Path(root).resolve()
    path = (root / record["image"]).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Image path escapes project directory")
    if record.get("image_sha256") and sha256(path) != record["image_sha256"]:
        raise ValueError(f"Crop checksum mismatch: {record['id']}")
    return path
