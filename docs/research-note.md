# A one-page pilot of historical financial handwriting

## Question

Can a modern English line recognizer preserve handwritten financial amounts in a nineteenth-century ledger, and how much does preprocessing affect its output?

## Evidence

A 4,666 x 7,091-pixel image was obtained through NYPL's public image service using image ID 57733030, identified in the Brown Brothers project's public illustration. The inspected page has cursive headings, monetary columns, ruled lines, and ditto marks. Twenty-two crops were selected manually. Draft labels were read from the source by the assistant and have not been independently human-reviewed. Therefore all numbers below are exploratory.

TrOCR-small was run on identical crop regions with original color, grayscale, and grayscale plus autocontrast. A published modern IAM test line served as a setup check: both tested variants had three character edits in 93 normalized reference characters (3.2%). This confirms a working inference path on one familiar-domain sample, not general recognition quality.

## Observations

Original-color crops yielded 300 character edits across 191 reference characters (157.1% CER). Grayscale reduced this to 79 edits (41.4%), and grayscale plus autocontrast to 71 edits (37.2%). These are comparisons against provisional labels from the same selected page. They do not establish performance on unseen historical pages.

The contrast variant's WER was 91.7%, slightly higher than grayscale's 89.6%, despite a lower CER. All three variants had zero literal exact crop matches. In the eight eligible numeric amount crops, preserved digit sequences increased from zero to two to four matches. This is a component measure, not proof that extracted financial values are valid.

Failure examples are inspectable in raw predictions and images. The date heading was read as an attorney-related phrase with year 1944 instead of the draft 1844. The draft amount `255 64` became `155.04` in the contrast run, changing digits as well as punctuation. A recognizable financial description retained most words but changed capitalization. Ditto marks generated extra symbols or text. These failures justify retaining image links and separating transcription from financial interpretation.

## Interpretation

On this pilot, color handling matters substantially. The grayscale-to-contrast improvement is smaller than the original-to-grayscale change, so describing the entire effect as a contrast improvement would conflate two interventions. More pages and independently reviewed references are needed to determine whether either method transfers. Low CER would not by itself justify financial analysis; exact field checks and source inspection remain necessary.

## Transkribus full-page experiment

Recognition completed with The English Eagle on the original full-resolution page. Text and PAGE XML were downloaded from the completed export job. The PAGE creator records model ID 53042, PyLaia platform version 2.51.0, and no language model. Four regions contain 97 recognized lines. Archive checksum, region reading order, line coordinates, and literal text are preserved in `output/transkribus/page-layout.json`; account metadata and hosted file URLs are omitted. The original archive remains local and excluded from Git. Input identity is based on the user-selected upload and matching dimensions, rather than a provider-reported input checksum.

The heading is recognized as `New Orleans February 1844`, matching the draft reading where TrOCR failed. Other lines contain changed names, digits, and monetary notation; `To Sundrus` illustrates a questionable description. Region ordering groups many amounts apart from their descriptions. A correct heading therefore does not establish a usable financial table. This is a separate page-level experiment. No Transkribus accuracy score or matched-crop comparison is claimed at this stage.

## Remaining work

Human-review the references; preserve disagreements and unresolved readings. Add distinct pages and freeze page-level splits. Run Transkribus on matching crop inputs or design a separate end-to-end page metric. Record provider model identity and preserve exported text/layout. Use resulting evidence to decide whether model adaptation, better segmentation, or targeted human review is the next useful intervention.
