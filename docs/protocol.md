# Recognition protocol

## Current scope

One Brown Brothers page, 22 manually selected crops: seven headings/text regions and fifteen amount regions. Eight amounts have fully numeric two-part draft labels; seven contain ditto marks. The page is a pilot, not a held-out evaluation sample. No recognition model is fine-tuned in this project.

The reference convention preserves case, abbreviations, punctuation, and literal monetary notation. A double-quote character represents the provisional reading of a ditto glyph. Those readings require human confirmation. Reference crops were drafted from the source image before model inference. They remain `reviewed=false`; automated transcription or an assistant's visual reading is not independent human ground truth.

The recognizer is `microsoft/trocr-small-handwritten`, public revision `b4648cfa171985a6745f37ddd637e98c0da958ac`. TrOCRProcessor uses the saved slow processor; the image processor handles resizing and normalization. Inference uses greedy decoding, `max_new_tokens=96`, and no additional fine-tuning. The run was on CPU with four PyTorch threads. Input variants are original RGB, replicated-channel grayscale, and replicated-channel grayscale after Pillow autocontrast with default cutoff. Equal crop bounds are used across methods.

## Measurement

Character error rate is total character edit distance divided by total reference characters. Word error rate uses whitespace-separated tokens and the same micro-average. Both can exceed one when insertions are numerous. Exact match preserves case, punctuation, ditto glyph convention, and digits. Normalization applies Unicode NFC and collapses whitespace.

Amount digit-sequence match measures an additional component: strip non-ASCII-digit characters from reference and hypothesis, then compare. Only reference amounts matching `[0-9]+ [0-9]{2}` qualify. This measures digit preservation, not decimal/currency interpretation; it can reward a prediction with extra non-digit text and must be read alongside literal exact match. Ditto amounts are excluded rather than resolved by assumption.

Missing predictions remain in the denominator and are scored against empty text. Unknown/duplicate IDs fail. Uncertain and empty references are excluded and counted. Reviewed references require reviewer attribution. Unreviewed references are excluded unless the caller explicitly requests an exploratory run. A page appearing in more than one split fails validation before scoring. Prediction image hashes, when supplied, must match the reference crop hashes.

## Next independent study

Freeze transcription conventions and review the pilot manually. Acquire distinct pages representing different hands and layouts. Assign page-level development and evaluation splits before tuning preprocessing or model choice. Use development data to select a method, then compare methods once on the frozen evaluation pages. Report sample sizes, raw errors, and field outcomes, not just the best aggregate.

A full-page recognition run includes line segmentation and reading order. Its errors must not be compared directly to the manual-crop recognizer as if the inputs and tasks were identical. For a direct provider comparison, run the provider on the same individual crop images and record input identities and exported outputs.
