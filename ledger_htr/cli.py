import argparse
import json
from pathlib import Path
from .data import read_jsonl, write_jsonl, sha256, resolve_crop
from .metrics import score


def fetch(args):
    import urllib.request
    from PIL import Image
    root = Path(args.root)
    manifest = json.loads((root / args.manifest).read_text())
    for page in manifest["pages"]:
        destination = (root / page["image"]).resolve()
        if not destination.is_relative_to(root.resolve()):
            raise ValueError("Source path escapes root")
        if destination.exists():
            if sha256(destination) != page["sha256"]:
                raise ValueError(f"Source checksum mismatch: {page['id']}")
            print(f"Verified existing {page['id']}")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(page["source_url"], headers={"User-Agent": "ledger-htr/0.1 research pilot"})
        with urllib.request.urlopen(request, timeout=40) as response:
            payload = response.read(25_000_001)
        if len(payload) > 25_000_000:
            raise ValueError("Source exceeds 25 MB pilot limit")
        import hashlib, io
        if hashlib.sha256(payload).hexdigest() != page["sha256"]:
            raise ValueError("Remote image changed; review and deliberately update source manifest")
        with Image.open(io.BytesIO(payload)) as image:
            if image.size != (page["width"], page["height"]):
                raise ValueError("Source dimensions changed")
            image.verify()
        destination.write_bytes(payload)
        print(f"Fetched and verified {page['id']}")


def crop(args):
    from PIL import Image
    root = Path(args.root)
    manifest = json.loads((root / args.manifest).read_text())
    sources = {r["id"]: r for r in manifest["pages"]}
    records = read_jsonl(root / args.plan)
    results = []
    # Check the complete plan before replacing any crops or their manifest.
    import re
    for row in records:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", row["id"]):
            raise ValueError("Crop id must be a safe filename")
        source = sources[row["page_id"]]
        box = row["bbox"]
        if len(box) != 4 or any(type(n) is not int for n in box):
            raise ValueError("bbox must contain four integer pixel coordinates")
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= source["width"] and 0 <= y0 < y1 <= source["height"]):
            raise ValueError(f"Invalid crop bounds for {row['id']}")
        if sha256(root / source["image"]) != source["sha256"]:
            raise ValueError("Source image checksum mismatch")
    for row in records:
        source = sources[row["page_id"]]
        image_path = root / source["image"]
        if sha256(image_path) != source["sha256"]:
            raise ValueError("Source image checksum mismatch")
        box = row["bbox"]
        if len(box) != 4 or any(type(n) is not int for n in box):
            raise ValueError("bbox must contain four integer pixel coordinates")
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= source["width"] and 0 <= y0 < y1 <= source["height"]):
            raise ValueError(f"Invalid crop bounds for {row['id']}")
        target = root / "data/crops" / f"{row['id']}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(image_path) as image:
            image.crop(box).convert("RGB").save(target)
        results.append({**row, "image": str(target.relative_to(root)), "image_sha256": sha256(target),
                        "source_sha256": source["sha256"]})
    write_jsonl(root / args.output, results)
    print(f"Wrote {len(results)} source-linked crops to {args.output}")


def infer(args):
    import time
    import torch
    from PIL import Image, ImageOps
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    root = Path(args.root)
    model_path = root / args.model
    processor = TrOCRProcessor.from_pretrained(model_path, local_files_only=True, use_fast=False)
    model = VisionEncoderDecoderModel.from_pretrained(model_path, local_files_only=True)
    device = "mps" if args.device == "auto" and torch.backends.mps.is_available() else ("cpu" if args.device == "auto" else args.device)
    model.to(device).eval()
    torch.set_num_threads(4)
    predictions = []
    for row in read_jsonl(root / args.references):
        with Image.open(resolve_crop(root, row)) as source:
            image = source.convert("RGB")
            if args.variant in {"grayscale", "contrast"}:
                image = ImageOps.grayscale(image)
                if args.variant == "contrast":
                    image = ImageOps.autocontrast(image)
                image = image.convert("RGB")
        start = time.perf_counter()
        pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)
        with torch.inference_mode():
            ids = model.generate(pixel_values, max_new_tokens=96, num_beams=1)
        text = processor.batch_decode(ids, skip_special_tokens=True)[0]
        predictions.append({"id": row["id"], "text": text, "variant": args.variant,
                            "model": "microsoft/trocr-small-handwritten", "revision": args.revision,
                            "device": device, "seconds": time.perf_counter() - start,
                            "image_sha256": row["image_sha256"]})
        print(f"{row['id']}: {text}", flush=True)
    write_jsonl(root / args.output, predictions)


def evaluate(args):
    root = Path(args.root)
    refs = read_jsonl(root / args.references)
    predictions = read_jsonl(root / args.predictions)
    by_id = {r["id"]: r for r in refs}
    for prediction in predictions:
        reference = by_id.get(prediction["id"])
        if reference and prediction.get("image_sha256") and prediction["image_sha256"] != reference.get("image_sha256"):
            raise ValueError("Prediction crop does not match reference crop")
    result = score(refs, predictions, args.split, args.include_unreviewed)
    result["reference_file_sha256"] = sha256(root / args.references)
    result["prediction_file_sha256"] = sha256(root / args.predictions)
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"scope": result["scope"], "overall": result["overall"]}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Historical ledger HTR study")
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("fetch"); p.add_argument("--manifest", default="data/source-manifest.json"); p.set_defaults(run=fetch)
    p = sub.add_parser("crop"); p.add_argument("--manifest", default="data/source-manifest.json"); p.add_argument("--plan", default="data/crop-plan.jsonl"); p.add_argument("--output", default="data/references.jsonl"); p.set_defaults(run=crop)
    p = sub.add_parser("infer"); p.add_argument("--references", default="data/references.jsonl"); p.add_argument("--model", default="models/trocr-small-handwritten"); p.add_argument("--revision", default="b4648cfa171985a6745f37ddd637e98c0da958ac"); p.add_argument("--variant", choices=["raw", "grayscale", "contrast"], default="raw"); p.add_argument("--device", choices=["auto", "cpu", "mps"], default="auto"); p.add_argument("--output", required=True); p.set_defaults(run=infer)
    p = sub.add_parser("evaluate"); p.add_argument("--references", default="data/references.jsonl"); p.add_argument("--predictions", required=True); p.add_argument("--split", choices=["pilot", "dev", "test"], default="test"); p.add_argument("--include-unreviewed", action="store_true"); p.add_argument("--output", required=True); p.set_defaults(run=evaluate)
    p = sub.add_parser("serve"); p.add_argument("--port", type=int, default=8765); p.set_defaults(run=lambda a: __import__("ledger_htr.review", fromlist=["serve"]).serve(Path(a.root), a.port))
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
