# North Dakota CTrack opinion feed

Native-Code-First Review:
- Need: Restore complete current North Dakota Supreme Court opinion discovery after the prior HTML listing stopped serving EX131.
- Search: Used rg across state/nd.py, the North Dakota legacy backscraper, state/nev.py, pyproject.toml, upstream code, and the installed Juriscraper dependency in EX131 site-packages; no generic CTrack SDK or adapter exists.
- Native option: Reuse the court's native public CTrack docket-entry API and direct document endpoint through installed OpinionSiteLinear, following the upstream state/nev.py adapter pattern.
- Gap: state/nd.py had no CTrack adapter, and its former HTML source now returns HTTP 403 from EX131.
- Decision: Extend the existing scraper with the narrow CTrack query, pagination, and shared-document deduplication behavior.
- Duplication check: This adds no loader, service, or separate ingestion path; historical coverage remains with the existing North Dakota backscraper.

Root-Cause Review:
- Symptom: The production North Dakota corpus stopped at April 9, 2026, although the court published later opinions through October 1, 2026.
- Root cause: The official-source endpoint invariant broke for the entire current North Dakota opinion class when the publisher migrated current opinions to CTrack but the source adapter retained the retired HTML URL.
- Evidence: The old URL returns HTTP 403 on EX131; CTrack docket-entry type 1000057 returns 110 post-cutoff rows, and all ten unique records in the rolling window return PDFs from the official endpoint.
- Scope: The affected class is every current North Dakota Supreme Court opinion in the CTrack era beginning April 8, 2024; known boundaries are that court and era, while older opinions remain on the legacy backscraper and consolidated dockets may share one PDF.
- Fix strategy: Repair the source-level adapter at the official-source boundary by querying CTrack by date, paging backscrapes, conserving every docket for shared PDFs, and retaining legacy HTML parsing.
- Regression test: The October 1 CTrack fixture covers nine unique opinions and a consolidated case sharing one PDF; both prior HTML fixtures remain and pass.
- Blast radius: Current North Dakota opinion discovery and CTrack-era backscrapes; rollback is the single scraper commit and no data migration or watermark change is involved.
