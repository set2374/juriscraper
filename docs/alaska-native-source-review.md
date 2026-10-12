# Alaska native appellate decision source review

## Native-Code-First Review:

- Need: Restore unattended Alaska Supreme Court and Court of Appeals coverage, including every nonprecedential decision category the court publishes.
- Search: Inspected `juriscraper/opinions/united_states/state/alaska.py`, `juriscraper/opinions/united_states/state/alaskactapp.py`, `juriscraper/AbstractSite.py`, the pre-Westlaw history of those paths, the Alaska Court System's current appellate publication pages, and upstream issue 2081.
- Native option: Reuse the Alaska Court System `CMSPublic` pages, the existing `OpinionSiteLinear` contract, the existing `httpx` transport and configured SOCKS egress, and the prior Alaska table parser model.
- Gap: The current modules depend on Westlaw, which returns 403. The court-native pages work when compression is disabled and expose decision categories Westlaw omitted.
- Decision: Restore and extend the prior native table parser in the two existing court modules. Request identity encoding so the existing transport remains usable.
- Duplication check: This adds no loader, service, transport, or parallel court module.

## Root-Cause Review:

- Symptom: Both enabled Alaska modules fail nightly with Westlaw 403 responses and report zero observed decisions.
- Root cause: The June migration replaced the court-native source with a third-party surface. The native gateway separately emits duplicate `Transfer-Encoding` headers for compressed `httpx` responses and rejects the default user agent.
- Evidence: Production traces show Westlaw 403. Live EX131 probes show that the native pages and PDFs return 200 through the approved U.S. egress with `Accept-Encoding: identity` and the `Free Law Project` user agent.
- Scope: Alaska Supreme Court and Court of Appeals slip opinions, memorandum opinions and judgments, published orders, summary dispositions, bail orders, and case-related orders. Other courts and transports are unchanged.
- Fix strategy: Restore the source-selection invariant at the official publisher boundary: point the two existing modules to every `CMSPublic` decision category, parse their shared table contract, filter the normal 30-day window, and request `showAll` only for backscrapes.
- Regression test: `tests/local/test_StateAlaskaScraperTest.py` covers category inventories, headers and transport, published and nonprecedential row shapes, date filtering, and backscrape URL behavior; `tests/examples/opinions/united_states/alaska_example.html` and `alaskactapp_example.html` cover the official-source fixture contract.
- Blast radius: Two Alaska modules and their fixtures. Rollback is one commit; the nightly source gate continues to fail closed if any category becomes unavailable.
