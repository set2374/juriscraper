"""Scraper for the Alaska Supreme Court.

CourtID: alaska
Court Short Name: Alaska

The Alaska Court System publishes slip opinions and the other appellate
decision categories on its native case-management site. The Supreme Court and
Court of Appeals use the same page shape; ``alaskactapp`` subclasses this
module and supplies the Court of Appeals endpoints.
"""

import re
from datetime import date, timedelta
from urllib.parse import urlencode, urljoin

from dateutil import parser
from typing_extensions import override

from juriscraper.AbstractSite import logger
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    base_url = "https://appellate-records.courts.alaska.gov/CMSPublic/"
    first_opinion_date = date(1960, 1, 1)
    days_interval = 30

    # These are the decision categories the court itself exposes from its
    # appellate opinions landing page. Memorandum opinions and judgments are
    # nonprecedential under Alaska Appellate Rule 214(d).
    source_pages: tuple[tuple[str, str], ...] = (
        ("Home/Opinions?isCOA=False", "Published"),
        ("Home/MOJOpinions?isCOA=False", "Unpublished"),
        ("Home/PublishedOrders?isCOA=False", "Published"),
    )

    whitespace_regex = re.compile(r"\s+")
    lower_court_regex = re.compile(
        r"""
        (?:
            Appeals?\s+from\s+the\s+|
            Appeals\s+in\s+File\s+Nos\.\s+S-\d+(?:/\d+)?\s+from\s+the\s+|
            Petitions?\s+for\s+Review\s+from\s+the\s+|
            Petition\s+for\s+Hearing\s+from\s+the\s+|
            Certified\s+(?:Original\s+Application\s+for\s+Relief\s+and\s+Jurisdiction\s+Transfer|Question)\s+from\s+the\s+
        )
        (?P<lower_court>.*?)(?=Judge\.|\n\s*\n)
        """,
        re.X | re.DOTALL,
    )
    lower_court_number_regex = re.compile(
        r"(?:Superior|District) Court Nos?\.?:?\s*"
        r"(\d[A-Z]{2}-\d{2}-\d{3,6}(?:/\d+)?\s+[A-Z]{2})"
    )
    panel_regex = re.compile(
        r"Before:\s*(?P<panel>.*?)\s*(?:Justices?|Judges?)\.", re.DOTALL
    )
    panel_title_regex = re.compile(
        r",?\s*(?:Chief\s+)?(?:Justices?|Judges?)\b"
    )
    panel_split_regex = re.compile(r",|\s+and\s+")
    judge_suffixes = ("Jr", "Sr", "II", "III", "IV")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=self.days_interval)
        self.is_backscrape = False
        self._seen_download_urls: set[str] = set()
        self.url = self._source_url(self.source_pages[0][0])

        # The court's gateway returns duplicate Transfer-Encoding headers for
        # compressed responses. Asking for the identity representation keeps
        # the normal httpx transport (and its configured SOCKS route) usable.
        # The site's gateway also rejects the default "Juriscraper" UA.
        self.request["headers"].update(
            {"Accept-Encoding": "identity", "User-Agent": "Free Law Project"}
        )
        self.needs_special_headers = True
        self.expected_content_types = ["application/pdf"]
        self.make_backscrape_iterable(kwargs)

    def _source_url(self, endpoint: str, *, show_all: bool = False) -> str:
        url = urljoin(self.base_url, endpoint)
        if show_all:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode({'showAll': 'True'})}"
        return url

    @override
    async def _process_html(self) -> None:
        self._parse_page(self.html, self.source_pages[0][1])
        if self.test_mode_enabled():
            return

        for endpoint, status in self.source_pages[1:]:
            tree = await self._get_html_tree_by_url(self._source_url(endpoint))
            self._parse_page(tree, status)

    def _parse_page(self, tree, status: str) -> None:
        """Parse one native decision-category page."""
        if tree is None:
            logger.warning("%s: native decision page was empty", self.court_id)
            return

        for table in tree.xpath(
            "//table[contains(@class, 'cms-opinion-table')]"
        ):
            headings = table.xpath("./preceding-sibling::h5[1]")
            if not headings:
                logger.warning(
                    "%s: decision table has no date heading", self.court_id
                )
                continue
            date_text = self.whitespace_regex.sub(
                " ", headings[0].text_content()
            ).strip()
            decision_date = parser.parse(date_text).date()
            if not self.test_mode_enabled() and not (
                self.start_date <= decision_date <= self.end_date
            ):
                continue

            for row in table.xpath(".//tbody/tr"):
                links = row.xpath(
                    ".//td[@headers='table_header_document']"
                    "//a[contains(@href, 'OpenOpinionDocument') or "
                    "contains(@href, 'OpenBailDocument')]/@href"
                )
                if not links:
                    logger.warning(
                        "%s: skipping native decision row without a document: %s",
                        self.court_id,
                        self.whitespace_regex.sub(
                            " ", row.text_content()
                        ).strip(),
                    )
                    continue

                download_url = urljoin(self.base_url, links[0])
                if download_url in self._seen_download_urls:
                    continue

                docket = self._cell_text(row, "table_header_case")
                name = self._cell_text(row, "table_header_title")
                if not docket or not name:
                    logger.warning(
                        "%s: skipping native decision row missing docket or name: %s",
                        self.court_id,
                        self.whitespace_regex.sub(
                            " ", row.text_content()
                        ).strip(),
                    )
                    continue

                case = {
                    "date": date_text,
                    "docket": docket,
                    "name": name,
                    "url": download_url,
                    "status": status,
                    "citation": self._cell_text(row, "table_header_reference"),
                }
                self.cases.append(case)
                self._seen_download_urls.add(download_url)

    def _cell_text(self, row, header: str) -> str:
        cells = row.xpath(f"./td[@headers='{header}']")
        if not cells:
            return ""
        return self.whitespace_regex.sub(" ", cells[0].text_content()).strip()

    async def _download_backwards(self, dates: tuple[date, date]) -> None:
        """Download all native categories and retain the requested date range."""
        self.start_date, self.end_date = dates
        self.is_backscrape = True
        self.cases = []
        self._seen_download_urls = set()
        logger.info(
            "Backscraping %s for range %s %s",
            self.court_id,
            self.start_date,
            self.end_date,
        )
        for endpoint, status in self.source_pages:
            tree = await self._get_html_tree_by_url(
                self._source_url(endpoint, show_all=True)
            )
            self._parse_page(tree, status)
        self.downloader_executed = True
        await self.parse()

    def extract_from_text(self, scraped_text: str) -> dict:
        """Extract lower-court and panel metadata from an Alaska decision."""
        metadata = {}

        lower_court_str = ""
        if match := self.lower_court_regex.search(scraped_text):
            lower_court_str = self.whitespace_regex.sub(
                " ", match.group("lower_court")
            ).strip()

        if lower_court_str:
            parts = [part.strip() for part in lower_court_str.split(",")]
            if "appeals" in parts[0].lower():
                lower_court = parts[0]
            else:
                lower_court = ", ".join(parts[:2])
            lower_court_judge = None
            if len(parts) > 1:
                lower_court_judge = parts[-2]
                if lower_court_judge == "Jr." and len(parts) > 2:
                    lower_court_judge = f"{parts[-3]} Jr."

            metadata["Docket"] = {"appeal_from_str": lower_court}
            if lower_court_judge:
                metadata.setdefault("OriginatingCourtInformation", {})[
                    "assigned_to_str"
                ] = lower_court_judge

        if number_match := self.lower_court_number_regex.search(scraped_text):
            lower_court_number = self.whitespace_regex.sub(
                " ", number_match.group(1)
            ).strip()
            metadata.setdefault("OriginatingCourtInformation", {})[
                "docket_number"
            ] = lower_court_number

        if panel_match := self.panel_regex.search(scraped_text):
            panel = self.panel_title_regex.sub("", panel_match.group("panel"))
            judges = []
            for judge in self.panel_split_regex.split(panel):
                judge = judge.strip(" .,")
                if not judge:
                    continue
                if judge in self.judge_suffixes and judges:
                    suffix = f"{judge}." if judge in ("Jr", "Sr") else judge
                    judges[-1] = f"{judges[-1]} {suffix}"
                else:
                    judges.append(judge)
            if judges:
                metadata.setdefault("OpinionCluster", {})["judges"] = (
                    ", ".join(judges)
                )

        return metadata
