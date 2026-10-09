"""Import Transkribus text exports for the same identified crop images."""
from pathlib import Path
from .data import sha256


def import_transkribus(directory, references, model_name):
    known = {r["id"]: r for r in references}
    results = []
    for path in sorted(Path(directory).glob("*.txt")):
        id = path.stem
        if id not in known:
            raise ValueError(f"Unknown crop export: {path.name}; filenames must match crop ids")
        results.append({"id": id, "text": path.read_text(encoding="utf-8-sig").strip(),
                        "model": model_name, "provider": "Transkribus", "variant": "raw",
                        "image_sha256": known[id]["image_sha256"], "export_sha256": sha256(path),
                        "scope": "Text exported for an identified crop; provider version may be unavailable"})
    if not results:
        raise ValueError("No identified .txt exports found")
    return results
