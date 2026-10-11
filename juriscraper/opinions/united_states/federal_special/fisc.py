import re
from datetime import date
from urllib.parse import unquote, urlencode, urljoin, urlparse

from typing_extensions import override

from juriscraper.AbstractSite import logger
from juriscraper.lib.html_utils import get_html_parsed_text
from juriscraper.lib.string_utils import convert_date_string
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    """Foreign Intelligence Surveillance Court public opinions.

    The court's public-filings page rejects the source-engine host and the
    provider corpus stops in 2016. The Intelligence Community's official
    declassification database publishes the same public decisions through a
    paginated search and is reachable from the source-engine host. Follow its
    indexed court documents and release records, excluding procedures,
    assessments, pleadings, and Court of Review decisions.
    """

    base_url = "https://www.intelligence.gov"
    search_queries = ("FISC opinion", "FISC order")
    supplemental_records: tuple[dict[str, str | bool], ...] = ()
    court_markers = ("fisc",)
    excluded_markers = (
        "fiscr",
        "fisc-r",
        "fisc review",
        "court of review",
    )
    decision_markers = ("opinion", "order", "decision", "judgment")
    excluded_document_markers = (
        "assessment",
        "annex",
        "brief",
        "declaration",
        "government's response",
        "government’s response",
        "implementation",
        "motion",
        "procedures",
        "report",
        "statement",
        "transcript",
    )
    full_date_re = re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2},?\s+\d{4}\b",
        re.I,
    )
    month_year_re = re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+(\d{4})\b",
        re.I,
    )
    numeric_date_re = re.compile(
        r"(?<!\d)(0?[1-9]|1[0-2])[-_](0?[1-9]|[12]\d|3[01])[-_]"
        r"(20\d{2}|\d{2})(?!\d)"
    )
    compact_date_re = re.compile(
        r"(?<!\d)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(20\d{2})(?!\d)"
    )
    day_month_name_re = re.compile(
        r"(?<!\d)(0?[1-9]|[12]\d|3[01])"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"(\d{2})(?!\d)",
        re.I,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.status = "Published"
        self.url = self._search_url(self.search_queries[0])
        self.should_have_results = True

    def _search_url(self, query: str) -> str:
        return (
            f"{self.base_url}/ic-on-the-record-database/advanced-search?"
            + urlencode({"q": query, "f": "1", "t[0]": "33"})
        )

    @override
    async def _download(self, request_dict=None):
        if self.test_mode_enabled():
            # Retain compatibility with the historical court-page fixture.
            return await OpinionSiteLinear._download(self, request_dict)

        records = []
        seen_urls = set()
        first_page = True
        for query in self.search_queries:
            page_url = self._search_url(query)
            while page_url:
                if first_page:
                    self.url = page_url
                    page = await OpinionSiteLinear._download(
                        self, request_dict
                    )
                    first_page = False
                else:
                    page = await self._get_html_tree_by_url(page_url)
                await self._collect_search_page(page, records, seen_urls)
                next_urls = page.xpath(
                    "//a[@aria-label='Go to next page']/@href"
                )
                page_url = next_urls[0] if next_urls else ""
        self._append_supplemental_records(records, seen_urls)
        return records

    def _append_supplemental_records(
        self,
        records: list[dict],
        seen_urls: set[str],
    ) -> None:
        """Add verified court records omitted by the declassification search."""
        for record in self.supplemental_records:
            url = self._canonical_opinion_url(str(record["url"]))
            if url in seen_urls:
                continue
            seen_urls.add(url)
            records.append({**record, "url": url})

    async def _collect_search_page(
        self,
        page,
        records: list[dict],
        seen_urls: set[str],
    ) -> None:
        session = self.request["session"]
        for item in page.xpath("//li[contains(@class, 'result__item')]"):
            anchors = item.xpath(
                ".//a[contains(@class, 'result__title-link')]"
            )
            if not anchors:
                continue
            anchor = anchors[0]
            title = " ".join(anchor.text_content().split())
            description = " ".join(
                item.xpath(
                    "string(.//*[contains(@class, 'result__description')])"
                ).split()
            )
            result_url = self._normalize_result_url(anchor.get("href", ""))
            is_document = bool(
                anchor.xpath(".//*[contains(@class, 'pdf-icon')]")
            )

            if is_document:
                if not self._document_result_belongs_to_court(
                    title, description
                ):
                    continue
                resolved = await self._resolve_document_url(
                    session, result_url
                )
                if resolved is None:
                    continue
                document_url, published = resolved
                self._append_record(
                    records,
                    seen_urls,
                    title,
                    document_url,
                    "",
                    require_pdf_suffix=False,
                    display_name=title,
                )
                continue

            if not self._release_result_is_candidate(title, description):
                continue
            response = await session.get(
                result_url,
                headers=self.request["headers"],
                timeout=30,
            )
            response.raise_for_status()
            release_page = get_html_parsed_text(response.text)
            for release_anchor in release_page.xpath("//a[@href]"):
                label = " ".join(release_anchor.text_content().split())
                decision_url = self._normalize_result_url(
                    urljoin(str(response.url), release_anchor.get("href"))
                )
                if self._link_belongs_to_court(label, decision_url):
                    self._append_record(
                        records,
                        seen_urls,
                        label,
                        decision_url,
                        "",
                    )

    def _normalize_result_url(self, url: str) -> str:
        """Repair root-relative asset links rewritten from a nested search URL."""
        absolute = urljoin(self.base_url, url)
        parsed = urlparse(absolute)
        asset_index = parsed.path.find("/assets/")
        if asset_index >= 0:
            return urljoin(self.base_url, parsed.path[asset_index:])
        return absolute

    async def _resolve_document_url(
        self, session, result_url: str
    ) -> tuple[str, str] | None:
        """Resolve the database's root-relative PDF redirects safely."""
        current_url = result_url
        for _ in range(4):
            response = await session.head(
                current_url,
                headers=self.request["headers"],
                timeout=30,
                follow_redirects=False,
            )
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    response.raise_for_status()
                current_url = self._normalize_result_url(
                    urljoin(current_url, location)
                )
                continue
            response.raise_for_status()
            if (
                "application/pdf"
                not in response.headers.get("content-type", "").lower()
            ):
                return None
            return (
                self._canonical_opinion_url(str(response.url)),
                response.headers.get("last-modified", ""),
            )
        raise ValueError(f"Too many redirects for {result_url}")

    @override
    def _process_html(self) -> None:
        if isinstance(self.html, list):
            self.cases.extend(self.html)
            return

        # Historical fixture and emergency compatibility with the court page.
        for row in self.html.xpath("//tr[td/a]"):
            links = row.xpath("td/a/text()")
            if len(links) < 2:
                continue
            filing_name, filename = links[0], links[-1]
            if "opinion" not in filing_name.casefold():
                continue
            docket = row.xpath("string(td[4])").strip()
            if not self._legacy_record_belongs_to_court(docket, filename):
                continue
            date_text = row.xpath("string(td[1])").strip()
            opinion_url = urljoin(self.url, row.xpath(".//a/@href")[-1])
            self.cases.append(
                {
                    "date": date_text,
                    "docket": docket,
                    "name": filing_name,
                    "url": opinion_url,
                }
            )

    def _belongs_to_court(self, text: str) -> bool:
        normalized = text.casefold()
        return any(
            marker in normalized for marker in self.court_markers
        ) and not any(marker in normalized for marker in self.excluded_markers)

    def _document_result_belongs_to_court(
        self, title: str, description: str
    ) -> bool:
        normalized_title = title.casefold()
        combined = f"{title} {description}"
        return (
            self._belongs_to_court(combined)
            and any(
                marker in combined.casefold()
                for marker in self.decision_markers
            )
            and not any(
                marker in normalized_title
                for marker in self.excluded_document_markers
            )
        )

    def _release_result_is_candidate(
        self, title: str, description: str
    ) -> bool:
        normalized_title = title.casefold()
        combined = f"{title} {description}"
        return (
            "release" in normalized_title
            and self._belongs_to_court(combined)
            and any(
                marker in combined.casefold()
                for marker in self.decision_markers
            )
            and "assessment" not in normalized_title
        )

    def _link_belongs_to_court(self, label: str, url: str) -> bool:
        normalized = f"{label} {urlparse(url).path}".casefold()
        return (
            urlparse(url).path.casefold().endswith(".pdf")
            and any(marker in normalized for marker in self.decision_markers)
            and any(marker in normalized for marker in self.court_markers)
            and not any(
                marker in normalized for marker in self.excluded_markers
            )
        )

    def _legacy_record_belongs_to_court(
        self, docket: str, filename: str
    ) -> bool:
        normalized = f"{docket} {filename}".casefold()
        return not any(
            marker in normalized for marker in self.excluded_markers
        )

    def _append_record(
        self,
        records: list[dict],
        seen_urls: set[str],
        label: str,
        url: str,
        published: str,
        *,
        require_pdf_suffix: bool = True,
        display_name: str | None = None,
    ) -> None:
        url = self._canonical_opinion_url(url)
        if url in seen_urls or (
            require_pdf_suffix and not self._link_belongs_to_court(label, url)
        ):
            return
        seen_urls.add(url)
        try:
            date_filed, approximate = self._opinion_date(label, url, published)
        except ValueError:
            logger.warning(
                "Skipping official decision without a defensible decision "
                "date: %s",
                url,
            )
            return
        slug = urlparse(url).path.rsplit("/", 1)[-1].removesuffix(".pdf")
        name = display_name or re.sub(
            r"\s+is available here$", "", label, flags=re.I
        )
        if not name.strip():
            name = re.sub(r"[_-]+", " ", unquote(slug)).strip()
        records.append(
            {
                "date": date_filed.isoformat(),
                "date_filed_is_approximate": approximate,
                "docket": f"Redacted-{slug}",
                "name": name,
                "url": url,
            }
        )

    @staticmethod
    def _canonical_opinion_url(url: str) -> str:
        parsed = urlparse(url)
        host = parsed.netloc.casefold()
        if host in {"intel.gov", "www.intel.gov", "intelligence.gov"}:
            return parsed._replace(netloc="www.intelligence.gov").geturl()
        return url

    @classmethod
    def _opinion_date(
        cls, label: str, url: str, published: str
    ) -> tuple[date, bool]:
        source = unquote(f"{label} {urlparse(url).path}")
        date_source = source.replace("_", " ")
        match = cls.full_date_re.search(date_source)
        if match:
            parsed = convert_date_string(match.group(0))
            assert parsed is not None
            return parsed, False

        match = cls.numeric_date_re.search(source)
        if match:
            month, day, year = match.groups()
            year = f"20{year}" if len(year) == 2 else year
            return date(int(year), int(month), int(day)), False

        match = cls.compact_date_re.search(source)
        if match:
            month, day, year = match.groups()
            return date(int(year), int(month), int(day)), False

        match = cls.day_month_name_re.search(source)
        if match:
            parsed = convert_date_string(
                f"{match.group(1)} {match.group(2)} 20{match.group(3)}"
            )
            assert parsed is not None
            return parsed, False

        match = cls.month_year_re.search(date_source)
        if match:
            parsed = convert_date_string(
                f"{match.group(1)} 1, {match.group(2)}"
            )
            assert parsed is not None
            return parsed, True

        year_match = re.search(r"\b(20\d{2})\b", source)
        if year_match:
            return date(int(year_match.group(1)), 1, 1), True

        if not published:
            raise ValueError(f"No opinion date available for {label!r}")
        parsed = convert_date_string(published, fuzzy=True)
        if parsed is None:
            raise ValueError(f"No opinion date available for {label!r}")
        return parsed, True
