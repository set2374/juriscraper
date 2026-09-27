# New York docket label extraction

Native-Code-First Review:
- Need: Preserve the docket numbers on New York opinion records while removing source markup that repeats the same label immediately.
- Search: Inspected `juriscraper/opinions/united_states/state/ny.py`, `nyappdiv_1st.py`, `OpinionSite.clean_docket_match`, and `tests/examples/opinions/united_states/nyappdiv_1st_example.html`; checked installed Juriscraper 3.0.41 on the Library host.
- Native option: Extend the existing New York scraper's search-row and opinion-text extraction paths; the installed parser already owns both fields.
- Gap: The source text can say `Index No. Index No.` or `Case No. Case No.`; the row path stores it verbatim and the opinion regex then misses the docket entirely.
- Decision: Extend the native New York scraper with one shared label cleanup used before row storage and opinion matching, leaving every docket number intact.
- Duplication check: No second loader, resolver, or display formatter is introduced; the existing scraper remains the only source of the extracted docket field.

Root-Cause Review:
- Symptom: A reader displays duplicated labels and mixed docket metadata for New York appellate cases, including a 2020 TCR opinion.
- Root cause: The publisher's source HTML repeats a docket label consecutively, while the scraper copies cell text and applies an opinion regex that cannot consume a repeated label.
- Evidence: Production `search_docket` has 10 `Index No. Index No.` and 16 `Case No. Case No.` values, all from `nyappdiv`; the source opinion HTML contains the same text. The new test failed on the unmodified fork and passes with this change.
- Scope: Affected New York scraper paths and any case with an immediately repeated recognized `No.` label; distinct labeled docket numbers and other jurisdictions remain untouched.
- Fix strategy: Clean adjacent duplicate labels at the native extraction source, before the docket is recorded or matched from opinion text, then reconcile existing public records separately.
- Regression test: `tests/local/test_ny_docket_labels.py` checks both extraction paths; the five New York fixture parsers still match their expected outputs, and the real 2020 public HTML yields the cleaned docket.
- Blast radius: This changes only New York docket strings with immediate repeated labels. The original opinion HTML stays preserved; existing database rows require a reviewed backfill with an undo manifest.
