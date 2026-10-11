import asyncio
from datetime import date

import httpx

from juriscraper.opinions.united_states.federal_special import fisc, fiscr


def test_fisc_and_fiscr_links_are_separated():
    fisc_site = fisc.Site()
    fiscr_site = fiscr.Site()
    fisc_url = (
        "https://www.intelligence.gov/assets/documents/702-documents/"
        "declassified/2025/FISC_Opinion_Cert_ABC_03182025_Redacted.pdf"
    )
    fiscr_url = (
        "https://www.intelligence.gov/assets/documents/702-documents/"
        "declassified/2023_FISC-R_ECSP_Opinion.pdf"
    )

    assert fisc_site._link_belongs_to_court(
        "March 18, 2025 FISC Cert ABC Opinion", fisc_url
    )
    assert not fisc_site._link_belongs_to_court(
        "2023 FISC-R Opinion", fiscr_url
    )
    assert fiscr_site._link_belongs_to_court("2023 FISC-R Opinion", fiscr_url)
    assert not fiscr_site._link_belongs_to_court(
        "March 18, 2025 FISC Cert ABC Opinion", fisc_url
    )


def test_non_opinion_release_documents_are_excluded():
    site = fisc.Site()
    assert not site._link_belongs_to_court(
        "NSA 2025 FISA Cert ABC Querying Procedures",
        "https://www.intelligence.gov/assets/NSA_QPs_2025.pdf",
    )


def test_rewritten_relative_asset_url_is_restored_to_site_root():
    site = fisc.Site()
    malformed = (
        "https://www.intelligence.gov/ic-on-the-record-database/declassified/"
        "assets/documents/FISC_Opinion.pdf"
    )
    assert site._normalize_result_url(malformed) == (
        "https://www.intelligence.gov/assets/documents/FISC_Opinion.pdf"
    )
    assert not site._link_belongs_to_court(
        "29th Joint Assessment of FISC Compliance",
        "https://www.intelligence.gov/assets/FISC_Assessment.pdf",
    )
    assert not site._document_result_belongs_to_court(
        "AG Mukasey 2008 Declaration",
        "Background discussion of a FISC opinion and order",
    )
    assert not site._document_result_belongs_to_court(
        "SIGINT Annex DODM 5240.01-A",
        "References a Foreign Intelligence Surveillance Court order",
    )


def test_opinion_date_prefers_decision_date_and_marks_partial_dates():
    exact, exact_is_approximate = fisc.Site._opinion_date(
        "March 18, 2025 FISC Cert ABC Opinion",
        "https://www.intelligence.gov/FISC_Opinion_Cert_ABC.pdf",
        "Thu, 11 Sep 2025 15:11:22 +0000",
    )
    filename_exact, filename_is_approximate = fisc.Site._opinion_date(
        "Redacted FISC Memorandum Opinion Order",
        "https://www.intelligence.gov/2024_Sep_FISC_Opinion_9-17-24.pdf",
        "Fri, 02 May 2025 10:30:37 +0000",
    )
    partial, partial_is_approximate = fisc.Site._opinion_date(
        "January 2025 FISC Opinion",
        "https://www.intelligence.gov/FISC_Opinion.pdf",
        "Fri, 11 Jul 2025 18:12:01 +0000",
    )

    assert exact == date(2025, 3, 18)
    assert exact_is_approximate is False
    assert filename_exact == date(2024, 9, 17)
    assert filename_is_approximate is False
    assert partial == date(2025, 1, 1)
    assert partial_is_approximate is True


def test_duplicate_release_links_are_conserved_once():
    site = fiscr.Site()
    records = []
    seen = set()
    intel_url = (
        "https://www.intel.gov/assets/documents/702-documents/"
        "declassified/FISCR%20Opinion%2016-01.pdf"
    )
    intelligence_url = (
        "https://www.intelligence.gov/assets/documents/702-documents/"
        "declassified/FISCR%20Opinion%2016-01.pdf"
    )

    site._append_record(
        records,
        seen,
        "FISCR's April 14, 2016 Opinion",
        intel_url,
        "Mon, 22 Aug 2016 19:24:48 +0000",
    )
    site._append_record(
        records,
        seen,
        "April 14, 2016 FISCR Opinion",
        intelligence_url,
        "Mon, 22 Aug 2016 19:24:48 +0000",
    )

    assert len(records) == 1
    assert records[0]["date"] == "2016-04-14"
    assert records[0]["date_filed_is_approximate"] is False


def test_verified_fiscr_supplements_preserve_dockets_and_deduplicate():
    site = fiscr.Site()
    duplicate_url = site.supplemental_records[0]["url"]
    records = [{"url": duplicate_url, "name": "existing"}]
    seen = {duplicate_url}

    site._append_supplemental_records(records, seen)

    assert len(records) == len(site.supplemental_records)
    supplements = records[1:]
    assert {record["docket"] for record in supplements} == {
        "FISCR 18-01",
        "FISCR 20-01",
        "FISCR Misc. 20-02",
    }
    assert all(
        record["date_filed_is_approximate"] is False
        for record in supplements
    )
    assert len({record["url"] for record in records}) == len(records)


def test_image_only_release_link_uses_official_filename_as_name():
    site = fisc.Site()
    records = []
    site._append_record(
        records,
        set(),
        "",
        "https://www.intelligence.gov/assets/FISC_Opinion_May_18_2012.pdf",
        "",
    )

    assert records[0]["name"] == "FISC Opinion May 18 2012"
    assert records[0]["date"] == "2012-05-18"


def test_percent_encoded_filename_supplies_decision_date():
    parsed, approximate = fisc.Site._opinion_date(
        "",
        "https://www.dni.gov/FISC%20Order%20September%204%202008.pdf",
        "",
    )

    assert parsed == date(2008, 9, 4)
    assert approximate is False


def test_filename_dates_cover_month_words_and_day_month_abbreviations():
    april, april_is_approximate = fisc.Site._opinion_date(
        "Redacted FISC Memorandum Opinion Order",
        "https://www.intelligence.gov/FISC_Memorandum_Opinion_April_2024.pdf",
        "Tue, 12 Nov 2024 18:13:10 +0000",
    )
    july, july_is_approximate = fiscr.Site._opinion_date(
        "FISC-R July 2019 Opinion",
        "https://www.intelligence.gov/2018_Cert_FISCR_Opinion_12Jul19.pdf",
        "Tue, 08 Oct 2019 14:06:31 +0000",
    )

    assert april == date(2024, 4, 1)
    assert april_is_approximate is True
    assert july == date(2019, 7, 12)
    assert july_is_approximate is False


def test_official_search_paginates_and_filters_documents():
    first_page = """
    <html><body><ul>
      <li class="result__item">
        <a class="result__title-link" href="/documents/january-2025">
          <span class="pdf-icon"></span>January 2025 FISC Opinion
        </a>
        <p class="result__description">FISC Title I Opinion and Order</p>
      </li>
      <li class="result__item">
        <a class="result__title-link" href="/releases/march-2025">
          ODNI Releases March 2025 FISC Opinion
        </a>
        <p class="result__description">FISC certification opinion</p>
      </li>
      <li class="result__item">
        <a class="result__title-link" href="/documents/assessment">
          <span class="pdf-icon"></span>29th Joint Assessment
        </a>
        <p class="result__description">Discusses a prior FISC opinion</p>
      </li>
    </ul>
    <a aria-label="Go to next page" href="?q=FISC+opinion&amp;start=20">
      Next
    </a></body></html>"""
    second_page = """
    <html><body><ul>
      <li class="result__item">
        <a class="result__title-link" href="/documents/september-order">
          <span class="pdf-icon"></span>September 2, 2021 FISC Order
        </a>
        <p class="result__description">
          Foreign Intelligence Surveillance Court Order
        </p>
      </li>
      <li class="result__item">
        <a class="result__title-link" href="/documents/fiscr-opinion">
          <span class="pdf-icon"></span>2023 FISC-R Opinion
        </a>
        <p class="result__description">Court of Review opinion</p>
      </li>
    </ul></body></html>"""
    release = """
    <html><body>
      <a href="assets/opinions/FISC_Opinion_03182025.pdf">
        March 18, 2025 FISC Opinion
      </a>
      <a href="/procedures/FISC_Querying_2025.pdf">
        FISC Querying Procedures
      </a>
      <a href="/opinions/2023_FISC-R_Opinion.pdf">
        2023 FISC-R Opinion
      </a>
    </body></html>"""

    def handler(request):
        if request.url.path.endswith("/advanced-search"):
            body = (
                second_page if request.url.params.get("start") else first_page
            )
            return httpx.Response(200, text=body, request=request)
        if request.url.path in {
            "/documents/september-order",
        }:
            return httpx.Response(
                200,
                headers={
                    "content-type": "application/pdf",
                    "last-modified": "Fri, 11 Jul 2025 18:12:01 GMT",
                },
                request=request,
            )
        if request.url.path == "/documents/january-2025":
            return httpx.Response(
                302,
                headers={"location": "assets/opinions/January_2025.pdf"},
                request=request,
            )
        if request.url.path == "/assets/opinions/January_2025.pdf":
            return httpx.Response(
                200,
                headers={
                    "content-type": "application/pdf",
                    "last-modified": "Fri, 11 Jul 2025 18:12:01 GMT",
                },
                request=request,
            )
        if request.url.path == "/releases/march-2025":
            if request.method == "HEAD":
                return httpx.Response(
                    200,
                    headers={"content-type": "text/html"},
                    request=request,
                )
            return httpx.Response(200, text=release, request=request)
        raise AssertionError(
            f"Unexpected request: {request.method} {request.url}"
        )

    async def parse():
        site = fisc.Site(transport=httpx.MockTransport(handler))
        site.search_queries = ("FISC opinion",)
        try:
            await site.parse()
            return site
        finally:
            await site.close_session()

    site = asyncio.run(parse())
    assert site.case_names == (
        "March 18, 2025 FISC Opinion",
        "January 2025 FISC Opinion",
        "September 2, 2021 FISC Order",
    )
    assert site.case_dates == (
        date(2025, 3, 18),
        date(2025, 1, 1),
        date(2021, 9, 2),
    )
    assert site.date_filed_is_approximate == (False, True, False)
