# ATR batch — gemini-300-final

- pages: **300**
- started: 2026-10-11T14:03:34+00:00
- wall time: 241.0 min

| model | read | skipped | failed | empty | looped | arguing | cut off | chars/page | s/page | wall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `gemini-3.8-flash` | 300 | 0 | 0 | 19 | 0 | 0 | 0 | 883 | 8.4 | 241.0 min |

**These columns are not quality.** There is no ground truth in this run, and characters per page measures how much a model wrote, not how much of it is right — a model that hallucinates fluently leads this table. Comparing the readings is the point; the numbers only say what each run cost and whether it completed. Measuring accuracy needs transcribed lines and `eval/linebench.py`.

_Rebuilt from the files in this directory, not observed as the run happened._ **The failed column is not trustworthy here**: a page that failed wrote nothing, and nothing is what a rebuilt report cannot see. It counts only results that are present and unreadable. Everything else — including the empty column, which a resumed run undercounts and this does not — is read from the results themselves.

## Pages that came back empty

- `gemini-3.8-flash`: 19 of 300 page(s) (6%)
  - Donaueschingen (via UB Freiburg)__lassberg-letter-0180__002
  - Donaueschingen (via UB Freiburg)__lassberg-letter-0299__002
  - Donaueschingen (via UB Freiburg)__lassberg-letter-0346__003
  - Marbach__HS00755433_150dpi__HS00755433_150dpi0005
  - Marbach__HS00787953_150dpi__HS00787953_150dpi_0094
  - Marbach__HS00787953_150dpi__HS00787953_150dpi_0290
  - Marbach__HS00926844_150dpi__HS00926844_0007
  - Staatsarchiv Thurgau__lassberg-letter-1383__DERIVAT_StATG_9-45__1-1___75-1_00109
  - Staatsarchiv Zürrich__499_hs_evan_scch_erledigt__Autogr_Bebler_G_135__Autogr_Bebler_G_135_0004
  - Staatsarchiv Zürrich__499_hs_evan_scch_erledigt__Ms_M_8_35__Ms_M_8_32_35_0035
  - Staatsarchiv Zürrich__499_hs_evan_scch_erledigt__Ms_V_312_78__Ms_V_312_78_0008
  - UB Bern__Mss_h_h_XLIV_180_32_169
  - UB Bern__Mss_h_h_XLIV_180_32_77
  - UB Bern__Mss_h_h_XXVI_105_5_40
  - Weimar__FA Hodel 236__Weimar__GSA_96_2725_Seite132
  - Weimar__FA Hodel 236__Weimar__GSA_96_2725_Seite574
  - blb lassberg__K 2911,107__page_0002
  - blb lassberg__K 2911,16__page_0052
  - blb lassberg__K 2911,93__page_0001

These are successes by every signal this runner has: a 200, no error, both files on disk, and `is_complete` will skip them on every later run. **Look at the images before reading anything into the number.** A blank verso or an envelope flap is genuinely empty, and knowing how many the corpus holds is worth having before extrapolating a cost per page. A *written* page that comes back empty is a defect no other column here would ever show — the segmenter found no lines on it (gateway), or the model answered the page with nothing at all (external reader). The second is a reading the prompt refused, not a page the model could not fetch: compare the same pages under another prompt before concluding anything about the corpus.

## Readings

300 page(s) per model — too many to put in one file. The transcriptions are in `/home/dh/agentic_historian/agentic_historian/data/vlm_test/gemini-300-final`, one `.txt` per page per model.
