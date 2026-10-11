# FISC and FISCR official-decision discovery

## Native-Code-First Review:

- Need: Restore current FISC and FISCR decision discovery after the court
  listing began rejecting the production source host.
- Search: Inspected `fisc.py`, `fiscr.py`, `AbstractSite.py`, `OpinionSiteLinear.py`, installed site-packages for httpx and lxml, dependency declarations in `pyproject.toml`, the provider corpus, official court dockets, and official Intelligence Community search, RSS, release pages, and PDFs from EX131.
- Native option: Reuse the installed `OpinionSiteLinear` and `AbstractSite` async HTTP client, lxml parser, linear case contract, and approximate-date field; no new dependency or HTTP implementation is needed.
- Gap: The old modules read only the blocked court listing. The provider corpus
  ends in 2016 for FISC and 2008 for FISCR. The official RSS exposes only ten
  recent entries, and the Intelligence Community search omits published 2018
  and 2020 FISCR orders and opinions that remain available as official PDFs.
- Decision: Extend the two native opinion modules. Walk the official paginated
  HTML search, follow its native release links, and conserve the bounded set of
  verified split-source FISCR records in the FISCR module itself.
- Duplication check: This extends the existing court modules and creates no parallel scraper, loader, service, ingestion path, parser stack, or HTTP client.

## Root-Cause Review:

- Symptom: Live production-host validation returned zero FISC/FISCR items while
  public 2018-2025 decisions exist, and the provider contains only six FISC and
  two FISCR clusters.
- Root cause: The source invariant failed because the native scrapers depended exclusively on an official court listing that rejects the production host, while the reachable declassification source is archive-incomplete for post-2016 FISCR dockets.
- Evidence: EX131 received the court-listing rejection; provider counts stopped
  at 2016/2008; paginated Intelligence Community searches returned current
  decision records; and ten omitted 2018/2020 court URLs returned HTTP 206,
  `application/pdf`, and `%PDF` bytes from EX131.
- Scope: The affected class is public FISC and FISCR judicial opinions and
  orders exposed by the official declassification search or the verified
  FISCR 18-01, FISCR 20-01, and FISCR Misc. 20-02 court records. Agency
  procedures, assessments, pleadings, declarations, briefs, transcripts,
  reports, and rule-administration documents remain excluded.
- Fix strategy: Restore the source invariant inside the existing native modules by walking every reachable official search page, resolving native PDF redirects, adding only verified split-source court records, preserving docket/date metadata, and conserving each official URL once.
- Date integrity: Prefer a decision date stated in the title or filename.
  Month-only dates are marked approximate. Do not treat migrated HTTP
  `Last-Modified` values as judicial filing dates. Skip a searchable record when
  no defensible decision date exists until verified metadata is available.
- Regression test: The unit test `tests/local/test_fisc_official_feed.py` covers court separation, excluded document classes, dates, alias deduplication, pagination, redirect repair, and supplemental metadata; the legacy HTML fixture and EX131 live canary cover boundary cases and PDF identity.
- Blast radius: Only the two disabled federal-special modules change. They stay
  disabled until their source-engine pin, live parse, corpus ingestion, and
  registry identity are separately tested and deployed. Rollback is one commit.
