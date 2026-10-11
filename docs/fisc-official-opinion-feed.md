# FISC and FISCR official-decision discovery

## Native-Code-First Review:

Reuse Review:

- Need: Give the existing FISC and FISCR opinion modules complete, downloadable
  official opinions and orders for nightly ingestion.
- Search: Inspected `fisc.py`, `fiscr.py`, `AbstractSite.py`, and installed dependencies declared in `pyproject.toml`,
  `OpinionSiteLinear.py`, the provider corpus, the Intelligence Community
  search, and every page and PDF link in the court's public-filings table from
  EX131.
- Native option: Reuse the existing court modules, their async HTTP client,
  lxml parsing, linear case contract, and the court's native paginated table.
- Gap: The court's public-filings table supplies exact filed dates, dockets,
  titles, and direct PDFs for recent records, but it omits older and
  certification opinions retained by the Intelligence Community archive. The
  archive's assets return PDF bytes to the ingestion host only when the
  existing Juriscraper special-header path identifies the client truthfully as
  `Juriscraper`; generic client identifiers receive HTTP 403 HTML responses.
- Decision: Configure and extend the two existing modules to union the two
  official sources. Crawl
  the court table through its native pagination, retain the archive's older
  records, use Juriscraper's native special-header support, split FISC from
  FISCR by docket/file identity, and admit only judicial opinions, orders,
  decisions, and judgments with defensible dates.
- Duplication check: This configures the two existing modules and their native
  HTTP/header hooks. It creates no parallel scraper, loader, service, HTTP
  client, or ingestion path.

## Root-Cause Review:

Root-Cause Review:

- Symptom: The scraper reported 38 FISC and 13 FISCR records, but native
  ingestion could download only ten manually listed FISCR PDFs. The other
  archive assets returned HTTP 403 HTML under the controller's generic client
  identifier and could not enter the opinion corpus.
- Root cause: The underlying source-delivery invariant depends on the
  requesting client identifier. The Intelligence Community asset server
  conditions access on that identifier, and Juriscraper already supports per-source
  special headers, but these modules did not enable that native path. The
  court table alone was also insufficient because it omits older and
  certification decisions that remain in the archive.
- Evidence: EX131 verified all 18 court-table pages and 354 public filings. A
  live combined-source canary returned 144 unique FISC records (110 court, 34
  archive) and 14 unique FISCR records (12 court, two archive), spanning 2002
  through 2025. Every one of the 158 selected URLs returned HTTP 200/206,
  a PDF content type, and `%PDF` bytes with the truthful `Juriscraper` client
  identifier. The same archive URLs returned HTTP 403 HTML with generic
  `CourtListener` and browser client identifiers.
- Scope: The affected class is official FISC and FISCR opinions, orders,
  decisions, and judgments published in either official surface. The court
  table covers public filings since June 2013; the archive extends the selected
  corpus to 2002 and includes certification opinions absent from the table.
  Motions, briefs, responses, notices, letters, petitions, applications,
  submissions, declarations, reports, transcripts, and procedures are not
  judicial decisions and remain excluded even when their titles mention an
  opinion or order.
- Fix strategy: Repair the source invariant by parsing the authoritative court
  row fields, preserving archive metadata for complementary records, and requesting archive assets through the
  native truthful-header hook, require official PDF hosts and paths,
  deduplicate by canonical filename and court-preferred overlap, exclude
  future or unsupported dates, and fail visibly if either source cannot be
  fetched.
- Regression test: Unit tests in `tests/local/test_fisc_official_feed.py` cover pagination,
  direct-PDF admission, court separation, false-positive party filings,
  duplicate conservation, malformed rows, and future dates. The saved fixture
  confirms that a response merely mentioning opinions and orders is excluded.
- Blast radius: Only the two federal-special opinion modules and their existing
  fixtures change. Rollback is one commit; no corpus, watermark, or service is
  mutated by the source change itself.

Some official archive files still lack a source-supported judicial date. They
remain excluded rather than inheriting an HTTP timestamp or a guessed date.
That fail-closed set is a known completeness gap for later source-supported
reconciliation; it does not reduce the 158 records verified by this change.
