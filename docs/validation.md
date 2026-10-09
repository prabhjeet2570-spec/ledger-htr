# Executed validation · 9 October 2026

- Python 3.12.14, macOS ARM64, CPU inference; exact installed dependencies recorded in `requirements.lock.txt`.
- `python -m pytest -q`: 25 tests passed. HTTP integration tests required permission to bind loopback sockets; the restricted run otherwise had 21 passes and four socket-permission setup errors. The successful run exercised all tests.
- Real source fetch verified 4,666 × 7,091 dimensions and source SHA-256. All 22 crops have recorded coordinates and image checksums.
- TrOCR-small's seven local model files are verified against the pinned revision manifest. Three inference runs completed; preserved outputs/reports are actual runs, not fixtures.
- One published IAM test line produced three character edits across 93 characters in both tested variants; this is a setup check, not a benchmark.
- Browser review flow exercised an invalid attribution save, successful draft persistence, reload, and prediction disclosure. No assistant draft was marked human-reviewed. Integration tests separately cover restart persistence, stale writes, cross-origin writes, and route confinement.
- The current reference-review screen and actual results chart were visually inspected. Screenshot is in `output/screenshots/reference-review.png`.
- Transkribus completed one full-page recognition with The English Eagle. Downloaded text/PAGE export has four regions and 97 lines, model ID 53042, platform version 2.51.0. The original archive is local/ignored; the research-only derivative preserves text, geometry, ordering, archive checksum, and declared source identity without account metadata.

## Research work still required

Independently review draft labels, retain unresolved readings, and collect distinct pages for development and untouched final evaluation. Transkribus has no accuracy score here: full-page recognition and manual crop recognition are different tasks. No fine-tuning, validated improvement claim, automatic financial-table extraction, or historical financial conclusion is claimed. Hosted model identity does not ensure the provider can reproduce identical inference later.
