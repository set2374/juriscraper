import re
from datetime import date
from urllib.parse import unquote, urlencode, urljoin, urlparse

from typing_extensions import override

from juriscraper.AbstractSite import logger
from juriscraper.lib.html_utils import get_html_parsed_text
from juriscraper.lib.string_utils import convert_date_string
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    """Foreign Intelligence Surveillance Court public decisions.

    The court's public-filings table is the authoritative source for opinions
    and orders published there since June 2013. The Intelligence Community's
    declassification archive supplies certification decisions and older
    records that are absent from the court table. Conserve the union while
    preferring court metadata when both sources publish the same decision.
    """

    base_url = "https://www.intelligence.gov"
    court_base_url = "https://www.fisc.uscourts.gov"
    court_url = f"{court_base_url}/public-filings"
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
    excluded_court_title_markers = (
        "application",
        "assessment",
        "brief",
        "certificate",
        "certification",
        "declaration",
        "implementation",
        "letter",
        "motion",
        "notice",
        "petition",
        "procedures",
        "report",
        "response",
        "statement",
        "submission",
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
        self.url = self.court_url
        # The archive serves PDFs to its truthful Juriscraper identity but
        # returns a 403 HTML page to the generic download User-Agent.
        self.needs_special_headers = True
        self.request["headers"]["User-Agent"] = self.user_agent
        self.should_have_results = True

    def _search_url(self, query: str) -> str:
        return (
            f"{self.base_url}/ic-on-the-record-database/advanced-search?"
            + urlencode({"q": query, "f": "1", "t[0]": "33"})
        )

    @override
    async def _download(self, request_dict=None):
        if self.test_mode_enabled():
            return await OpinionSiteLinear._download(self, request_dict)

        records: list[dict] = []
        seen_urls: set[str] = set()
        seen_pages: set[str] = set()
        page_url = self.court_url
        first_page = True

        while page_url and page_url not in seen_pages:
            seen_pages.add(page_url)
            if first_page:
                page = await OpinionSiteLinear._download(self, request_dict)
                first_page = False
            else:
                page = await self._get_html_tree_by_url(page_url)
            self._collect_court_page(page, records, seen_urls)
            next_urls = page.xpath("//a[@title='Go to next page']/@href")
            page_url = urljoin(page_url, next_urls[0]) if next_urls else ""

        for query in self.search_queries:
            page_url = self._search_url(query)
            seen_search_pages: set[str] = set()
            while page_url and page_url not in seen_search_pages:
                seen_search_pages.add(page_url)
                page = await self._get_html_tree_by_url(page_url)
                await self._collect_search_page(page, records, seen_urls)
                next_urls = page.xpath(
                    "//a[@aria-label='Go to next page']/@href"
                )
                page_url = urljoin(page_url, next_urls[0]) if next_urls else ""
        return self._deduplicate_records(records)

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

    def _collect_court_page(
        self,
        page,
        records: list[dict],
        seen_urls: set[str],
    ) -> None:
        """Collect judicial decisions from the court's native table."""
        for row in page.xpath("//table//tbody/tr"):
            cells = row.xpath("./td")
            if len(cells) < 5:
                continue

            date_text = " ".join(cells[0].text_content().split())
            title = " ".join(cells[2].text_content().split())
            docket = " ".join(cells[3].text_content().split())
            file_name = " ".join(cells[4].text_content().split())
            file_links = cells[4].xpath(".//a/@href")
            if not file_links or not self._court_record_belongs_to_court(
                title, docket, file_name
            ):
                continue

            opinion_url = self._canonical_opinion_url(
                urljoin(self.court_url, file_links[-1])
            )
            if opinion_url in seen_urls or not self._is_official_court_pdf(
                opinion_url
            ):
                continue

            date_filed = convert_date_string(date_text)
            if date_filed is None or date_filed > date.today():
                continue

            seen_urls.add(opinion_url)
            records.append(
                {
                    "date": date_filed.isoformat(),
                    "date_filed_is_approximate": False,
                    "docket": docket,
                    "name": title,
                    "url": opinion_url,
                }
            )

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

        records: list[dict] = []
        self._collect_court_page(self.html, records, set())
        self.cases.extend(records)

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

    def _court_record_belongs_to_court(
        self, title: str, docket: str, filename: str
    ) -> bool:
        """Distinguish judicial decisions from filings citing decisions."""
        normalized_title = title.casefold()
        decision_positions = [
            normalized_title.find(marker)
            for marker in self.decision_markers
            if marker in normalized_title
        ]
        if not decision_positions:
            return False
        excluded_positions = [
            normalized_title.find(marker)
            for marker in self.excluded_court_title_markers
            if marker in normalized_title
        ]
        return (
            not excluded_positions
            or min(decision_positions) < min(excluded_positions)
        ) and self._legacy_record_belongs_to_court(docket, filename)

    @classmethod
    def _is_official_court_pdf(cls, url: str) -> bool:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https"
            and parsed.netloc.casefold()
            in {"fisc.uscourts.gov", "www.fisc.uscourts.gov"}
            and parsed.path.casefold().startswith("/sites/default/files/")
            and parsed.path.casefold().endswith(".pdf")
        )

    @classmethod
    def _deduplicate_records(cls, records: list[dict]) -> list[dict]:
        """Prefer court metadata and conserve each official document once."""
        deduplicated: list[dict] = []
        seen_urls: set[str] = set()
        seen_filenames: set[str] = set()
        court_signatures: set[tuple[str, tuple[str, ...]]] = set()

        for record in records:
            url = cls._canonical_opinion_url(str(record["url"]))
            parsed = urlparse(url)
            normalized_filename = re.sub(
                r"[^a-z0-9]+",
                "",
                unquote(parsed.path.rsplit("/", 1)[-1]).casefold(),
            )
            name = str(record.get("name", "")).casefold()
            kinds = tuple(
                marker for marker in cls.decision_markers if marker in name
            )
            signature = (str(record.get("date", "")), kinds)
            is_court_record = parsed.netloc.casefold() in {
                "fisc.uscourts.gov",
                "www.fisc.uscourts.gov",
            }

            if url in seen_urls or normalized_filename in seen_filenames:
                continue
            if not is_court_record and kinds and signature in court_signatures:
                continue

            record["url"] = url
            deduplicated.append(record)
            seen_urls.add(url)
            seen_filenames.add(normalized_filename)
            if is_court_record and kinds:
                court_signatures.add(signature)

        return deduplicated

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
        if host == "fisc.uscourts.gov":
            return parsed._replace(netloc="www.fisc.uscourts.gov").geturl()
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
