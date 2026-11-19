# Litigus fork: upstream sync to juriscraper v4.0.4 (2026-11-19)

This branch merges upstream `freelawproject/juriscraper` tag `v4.0.4` into the
Litigus fork at our production pin `bd9a7b5ccc` (29 Litigus commits ahead, 184
upstream commits behind). The large added files the commit gate lists are
upstream's own code arriving through the merge, not new Litigus code.

Native-Code-First Review:
- Need: the Arizona Supreme Court and Court of Appeals Division 1 scrapers 404 every night since 2026-10-20 because the azcourts.gov opinions API now requires a `pageSize` parameter.
- Search: upstream `juriscraper/opinions/united_states/state/ariz.py` history (commit 6add605cc, "fix(ariz): Send pageSize param now required by opinions API", fixes upstream #2357, first released in v4.0.2); installed package in the production `cl-django` image is juriscraper 3.0.44 from our fork pin `bd9a7b5ccc` (`/opt/litigus/source-engine/pyproject.toml:145`); fork has no newer branch with the fix.
- Native option: the upstream release that already contains the fix (v4.0.4, latest 4.x tag).
- Gap: none in upstream; the gap is only that our pin predates it.
- Decision: reuse; merge the upstream release into the fork instead of writing our own Arizona patch.
- Duplication check: no Litigus code is added for Arizona; the four conflict resolutions keep existing Litigus fixes (Alaska, North Dakota, Tennessee) and take upstream wording or typing where both sides changed the same lines.

Root-Cause Review:
- Symptom: `ariz` and `arizctapp_div_1` fail in every native-opinion sweep with HTTP 404 from `/API/Azcourts/Opinions/GetOpinions` (sweep 20261118T080012Z journal).
- Root cause: the publisher changed its API contract on 2026-10-20 so requests without `pageSize` 404; our pinned scraper predates the change.
- Evidence: sweep journal tracebacks (404 on GetOpinions for both courts); upstream commit 6add605cc message and diff adding `"pageSize": "10"` to `Site.params`.
- Scope: the defect generalizes to every scraper that inherits `ariz.Site.params` (ariz and arizctapp_div_1) and is bounded to them; arizctapp_div_2 uses a different source and is unaffected. Other upstream fixes between 3.0.44 and 4.0.4 arrive with the merge.
- Fix strategy: take the upstream source fix, which sends the required `pageSize` parameter in the scraper's own request, through the merge.
- Regression test: the upstream ariz example fixture test in `tests/local/test_ScraperExampleTest.py` and the full `tests/local` suite run on the owned EX131 lane before the image is rebuilt; the nightly native-opinion sweep is the live canary and must show both Arizona scrapers succeeding.
- Blast radius: the merge changes many scrapers at once. Rollback is repinning `pyproject.toml`/`uv.lock` in the CourtListener checkout to `bd9a7b5ccc` and rebuilding the image; the nightly baseline report lists any new failures or recoveries per court.
