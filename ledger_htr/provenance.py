import json
from pathlib import Path
from .data import sha256

MODEL_ID = "microsoft/trocr-small-handwritten"
MODEL_REVISION = "b4648cfa171985a6745f37ddd637e98c0da958ac"


def record_model(root, model_path):
    root, model_path = Path(root), Path(model_path)
    files = {p.name: sha256(p) for p in sorted(model_path.iterdir()) if p.is_file()}
    manifest = {"repository": MODEL_ID, "revision": MODEL_REVISION, "files": files}
    (root / "data/model-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def verify_model(root, model_path):
    manifest = json.loads((Path(root) / "data/model-manifest.json").read_text())
    if manifest["repository"] != MODEL_ID or manifest["revision"] != MODEL_REVISION:
        raise ValueError("Unexpected model identity or revision")
    for name, digest in manifest["files"].items():
        if Path(name).name != name:
            raise ValueError("Invalid model filename")
        if sha256(Path(model_path) / name) != digest:
            raise ValueError(f"Model checksum mismatch: {name}")
    return manifest
