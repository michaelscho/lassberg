# ATR batch — atr_trocr_corpus

- pages: **899**
- started: 2026-09-17T06:30:47+00:00
- wall time: 522.1 min

| model | read | skipped | failed | empty | cut off | chars/page | s/page | wall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `trocr-kurrent` | 899 | 0 | 0 | 77 | 0 | 844 | 38.0 | 522.1 min |

**These columns are not quality.** There is no ground truth in this run, and characters per page measures how much a model wrote, not how much of it is right — a model that hallucinates fluently leads this table. Comparing the readings is the point; the numbers only say what each run cost and whether it completed. Measuring accuracy needs transcribed lines and `eval/linebench.py`.

_Rebuilt from the files in this directory, not observed as the run happened._ **The failed column is not trustworthy here**: a page that failed wrote nothing, and nothing is what a rebuilt report cannot see. It counts only results that are present and unreadable. Everything else — including the empty column, which a resumed run undercounts and this does not — is read from the results themselves.

## Pages that came back empty

- `trocr-kurrent`: 77 of 899 page(s) (9%)
  - Aarau__upload__lassberg-letter-0884__00011-scan_2025-03-21_11-10-56l
  - Aarau__upload__lassberg-letter-0970__00008-scan_2025-03-21_13-08-51r
  - Aarau__upload__lassberg-letter-1126__00024-scan_2025-03-21_11-12-06r
  - Aarau__upload__lassberg-letter-1147__00029-scan_2025-03-21_11-12-40l
  - Aarau__upload__lassberg-letter-1407__00059-scan_2025-03-21_11-15-44l
  - Aarau__upload__lassberg-letter-1855__00079-scan_2025-03-21_12-03-36l
  - Aarau__upload__lassberg-letter-1855__00080-scan_2025-03-21_12-03-37r
  - Aarau__upload__lassberg-letter-1869__00085-scan_2025-03-21_12-04-05l
  - Aarau__upload__lassberg-letter-2232__00091-scan_2025-03-21_12-05-03l
  - Aarau__upload__lassberg-letter-2232__00092-scan_2025-03-21_12-05-04r
  - Aarau__upload__lassberg-letter-2474__00012-scan_2025-03-21_13-09-40r
  - Aarau__upload__lassberg-letter-2474__00013-scan_2025-03-21_13-09-53l
  - Aarau__upload__lassberg-letter-2915__00006-scan_2025-03-21_12-31-58l
  - Basel__lassberg-letter-2052__PA 82a B 9_Seite_200
  - Basel__lassberg-letter-2052__PA 82a B 9_Seite_201
  - Briefe UB Freiburg__lassberg-letter-0000-1814-04-30__003
  - Briefe UB Freiburg__lassberg-letter-0071__004
  - Briefe UB Freiburg__lassberg-letter-0078__004
  - Briefe UB Freiburg__lassberg-letter-0079__003
  - Briefe UB Freiburg__lassberg-letter-0079__004
  - … 57 more (see `manifest.jsonl`)

These are successes by every signal this runner has: a 200, no error, both files on disk, and `is_complete` will skip them on every later run. **Look at the images before reading anything into the number.** A blank verso or an envelope flap is genuinely empty, and knowing how many the corpus holds is worth having before extrapolating a cost per page; a written page that comes back empty means the segmenter found no lines on it, which no other column in this report would ever show.

## Readings

899 page(s) per model — too many to put in one file. The transcriptions are in `/home/dh/agentic_historian/agentic_historian/data/vlm_test/atr_trocr_corpus`, one `.txt` per page per model.
