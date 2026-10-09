"""Declared text normalization and micro-averaged edit-distance metrics."""
import unicodedata
from .data import validate_references


def normalize(text):
    # Retain case, punctuation, abbreviations, and digits; collapse whitespace only.
    return " ".join(unicodedata.normalize("NFC", text).split())


def edit_distance(reference, hypothesis):
    previous = list(range(len(hypothesis) + 1))
    for i, token in enumerate(reference, 1):
        current = [i]
        for j, other in enumerate(hypothesis, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (token != other)))
        previous = current
    return previous[-1]


def score(references, predictions, split="test", include_unreviewed=False):
    validate_references(references)
    known = {r["id"] for r in references}
    predicted = {}
    for row in predictions:
        if row["id"] in predicted:
            raise ValueError(f"Duplicate prediction: {row['id']}")
        if row["id"] not in known:
            raise ValueError(f"Unknown prediction id: {row['id']}")
        if not isinstance(row.get("text"), str):
            raise ValueError("Prediction text must be a string")
        predicted[row["id"]] = row["text"]
    selected = [r for r in references if r["split"] == split]
    eligible = [r for r in selected if (r["reviewed"] or include_unreviewed)
                and not r.get("uncertain", False) and normalize(r["text"])]
    if not eligible:
        raise ValueError("No eligible references; manually review labels before scoring")
    details = []
    for row in eligible:
        ref = normalize(row["text"])
        hyp = normalize(predicted.get(row["id"], ""))
        details.append({"id": row["id"], "page_id": row["page_id"], "kind": row["kind"],
                        "reference": ref, "prediction": hyp,
                        "missing": row["id"] not in predicted,
                        "reviewed": row["reviewed"],
                        "character_errors": edit_distance(ref, hyp),
                        "reference_characters": len(ref),
                        "word_errors": edit_distance(ref.split(), hyp.split()),
                        "reference_words": len(ref.split()), "exact_match": ref == hyp})

    def aggregate(group):
        chars = sum(r["reference_characters"] for r in group)
        words = sum(r["reference_words"] for r in group)
        return {"count": len(group), "character_errors": sum(r["character_errors"] for r in group),
                "reference_characters": chars,
                "cer": sum(r["character_errors"] for r in group) / chars,
                "wer": sum(r["word_errors"] for r in group) / words,
                "exact_match": sum(r["exact_match"] for r in group) / len(group),
                "coverage": sum(not r["missing"] for r in group) / len(group)}

    return {"scope": "exploratory-unreviewed" if any(not r["reviewed"] for r in details) else "reviewed-reference",
            "split": split, "normalization": "Unicode NFC; collapsed whitespace; case and punctuation retained",
            "excluded_reference_count": len(selected) - len(eligible), "overall": aggregate(details),
            "by_page": {p: aggregate([r for r in details if r["page_id"] == p]) for p in sorted({r["page_id"] for r in details})},
            "by_kind": {k: aggregate([r for r in details if r["kind"] == k]) for k in sorted({r["kind"] for r in details})},
            "details": details}
