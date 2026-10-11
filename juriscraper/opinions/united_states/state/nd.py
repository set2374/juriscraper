# Author: Phil Ardery
# Contact: https://www.ndcourts.gov/contact-us
# History:
# Date created: 2019-02-28
# Updated: 2024-05-08, grossir: to OpinionSiteLinear and new URL
# Updated: 2025-07-02, luism: get citation from HTML
# Updated: 2025-09-01, luism: extract lower court information from text

import re
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urlencode, urljoin

from typing_extensions import override

from juriscraper.AbstractSite import logger
from juriscraper.lib.string_utils import normalize_dashes
from juriscraper.lib.utils import PaginatedHtmlBackscrapeSite
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear, PaginatedHtmlBackscrapeSite[Any]):
    # Index: https://www.ndcourts.gov/supreme-court/opinions
    legacy_base_url = "https://www.ndcourts.gov/"
    base_url = (
        "https://portal-api.ctrack.ndcourts.gov/"
        "courts/cms/docketentrydocuments"
    )
    document_url = (
        "https://portal-api.ctrack.ndcourts.gov/courts/{court}/cms/case/"
        "{case}/docketentrydocuments/{document}"
    )
    court_uuid = "68f021c4-6a44-4735-9a76-5360b2e8af13"
    opinion_type_id = "1000057"
    ordered_fields = [
        "citation",
        "name",
        "docket",
        "date",
        "nature_of_suit",
        "judge",
    ]
    # The public CTrack appellate system launched April 8, 2024. Older
    # opinions remain covered by the dedicated North Dakota backscraper.
    first_opinion_date = datetime(2024, 4, 8)
    days_interval = 30
    name_regex = re.compile(r"^(.*?)(\s*(\d{4}\sND\s\d+))\s*$")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.status = "Published"
        self.page_size = 200
        self.document_case_indexes: dict[str, int] = {}
        self.document_dockets: dict[str, set[str]] = {}
        today = date.today()
        self.set_url(0, today - timedelta(days=self.days_interval), today)
        self.request["headers"].update(
            {
                "Accept": "application/json",
                "Referer": "https://portal.ctrack.ndcourts.gov/",
            }
        )
        self.expected_content_types = ["application/pdf"]
        self.make_backscrape_iterable(kwargs)
        self.should_have_results = True

    def set_url(
        self,
        page: int = 0,
        start: date | None = None,
        end: date | None = None,
    ) -> None:
        """Build a public CTrack opinion-document search URL."""
        params = {
            "docketEntryHeader.docketEntryTypeID": self.opinion_type_id,
            "caseHeader.courtID": self.court_uuid,
            "page": page,
            "size": self.page_size,
            "sort": "docketEntryHeader.filedDate,desc",
        }
        if start is not None:
            params["docketEntryHeader.docketEntryFiledDateFrom"] = (
                f"{start.isoformat()}T00:00:00.000Z"
            )
        if end is not None:
            params["docketEntryHeader.docketEntryFiledDateTo"] = (
                f"{(end + timedelta(days=1)).isoformat()}T00:00:00.000Z"
            )
        self.url = f"{self.base_url}?{urlencode(params)}"

    @override
    async def _process_html(self) -> None:
        if isinstance(self.html, dict):
            self._process_ctrack_results()
            return

        self._process_legacy_html()

    def _process_ctrack_results(self) -> None:
        """Build cases from the court's public CTrack document feed."""
        if not isinstance(self.html, dict):
            raise TypeError("CTrack response must be a JSON object")

        for result in self.html.get("_embedded", {}).get("results", []):
            entry = result["docketEntryHeader"]
            header = result["caseHeader"]
            if entry.get("securedDocument"):
                logger.warning(
                    "%s: skipping secured document for docket %s",
                    self.court_id,
                    header["caseNumber"],
                )
                continue

            document_id = result["documentLinkUUID"]
            docket = header["caseNumber"]
            if document_id in self.document_case_indexes:
                self.document_dockets[document_id].add(docket)
                case_index = self.document_case_indexes[document_id]
                self.cases[case_index]["docket"] = ", ".join(
                    sorted(self.document_dockets[document_id])
                )
                continue

            case_index = len(self.cases)
            self.document_case_indexes[document_id] = case_index
            self.document_dockets[document_id] = {docket}
            self.cases.append(
                {
                    "date": entry["filedDate"][:10],
                    "per_curiam": False,
                    "author": "",
                    "judge": "",
                    "summary": "",
                    "name": header["caseTitle"].strip(),
                    "citation": "",
                    "docket": docket,
                    "nature_of_suit": header.get("caseCategory", ""),
                    "url": self.document_url.format(
                        court=self.court_uuid,
                        case=header["caseInstanceUUID"],
                        document=document_id,
                    ),
                }
            )

    def _process_legacy_html(self) -> None:
        """Parse the retired HTML listing retained in historical fixtures.

        Most values are inside a <p>: whitespace and
        field names need to be cleaned

        Citation used to be available, now must be got from inside
        the document's text
        """
        # Consolidated cases return the same document once per each base docket
        # This may cause the scrape to abort prematurely due to number of
        # consecutive duplicates
        seen_urls = set()

        for row in self.html.xpath('//table//div[@class="row"]'):
            onclick = row.xpath(".//button[@onclick]/@onclick")
            if not onclick:
                logger.info("Skipping row without a 'View Opinion' button")
                continue

            raw_name, *values = list(
                map(str.strip, row.xpath("./div[1]/p[1]/text()"))
            )

            # Do the URL check
            url = urljoin(
                self.legacy_base_url,
                onclick[0].split("'")[1],
            )
            if url in seen_urls:
                logger.info(
                    "Skipping %s, we already have a case with url %s",
                    raw_name,
                    url,
                )
                continue
            seen_urls.add(url)

            docket, date, nature, author = [
                txt.split(":", 1)[1].strip() for txt in values if txt
            ]

            if match := self.name_regex.search(raw_name):
                case_name = match.group(1).strip()
                citation = match.group(2).strip()
                raw_name = case_name
            else:
                citation = ""

            case_name, other_docket = self.clean_name(raw_name)

            if other_docket:
                docket = f"{docket}, {other_docket}"

            per_curiam = False
            if "per curiam" in author.lower():
                author = ""
                per_curiam = True

            summary = ""
            if summary_texts := row.xpath("./div[2]/p[1]/text()"):
                summary = " ".join(summary_texts).strip()

            self.cases.append(
                {
                    "date": date,
                    "per_curiam": per_curiam,
                    "author": author,
                    "judge": author,
                    "summary": summary,
                    "name": case_name,
                    "citation": citation,
                    "docket": docket,
                    "nature_of_suit": nature,
                    "url": url,
                }
            )

    def clean_name(self, name: str) -> tuple[str, str]:
        """Cleans case name

        Some case names list the consolidated docket or a
        (CONFIDENTIAL) parentheses

        :param name: raw case name
        :return: cleaned name and extra_docket numbers
        """
        other_dockets = ""
        if "(consolidated w/" in name:
            other_dockets = ",".join(re.findall(r"\d{8}", name))
            name = name.split("(consolidated w/")[0]
        if "(CONFIDENTIAL" in name:
            name = name.split("(CONFIDENTIAL")[0]

        return name.strip(), other_dockets

    def extract_from_text(self, scraped_text: str) -> dict:
        """Extract model fields from opinion's document text

        Most times, the citations are available in the HTML; sometimes, they
        are only listed on the text

        For case_name and docket_number, even if they are available
        in the HTML, the document's text has the best values
        for consolidated cases, where the HTML lists partial
        case names and partial docket numbers

        :param scraped_text: Text of scraped content
        :return: Dict with keys of model's names, and values as dicts
        of models field - value pairs
        """
        metadata = {}
        regex = r"20\d{2}\sND\s\d+"
        citation_match = re.search(regex, scraped_text[:1000])

        if citation_match:
            metadata["Citation"] = citation_match.group(0)

        # Most times, paragraphs are enumerated. The data we are interested
        # in is in a few lines before the first paragraph
        lines = scraped_text.split("\n")
        found = False
        for index, line in enumerate(lines):  # noqa: B007
            if "[¶1]" in line:
                found = True
                break

        if not found:
            return metadata

        case_name, docket_number = "", ""
        reversed_lines = lines[:index][::-1]
        for index, line in enumerate(reversed_lines):
            if re.search(r"\d{8}", line):
                docket_number = line.strip()
                case_name = reversed_lines[index + 1].strip()
                break

        lower_court_pattern = re.compile(
            r"Appeal\s+from\s+the\s+(?P<lower_court>.*?),\s*the\s+Honorable\s+(?P<judge>.+?),\s*Judge",
            re.DOTALL,
        )

        lower_court = ""
        lower_court_judge = ""
        if match := lower_court_pattern.search(scraped_text):
            lower_court = re.sub(
                r"\s+", " ", match.group("lower_court")
            ).strip()
            lower_court_judge = match.group("judge").strip()

        # We only put keys into the objects when they exist
        # Otherwise, we would overwrite existing data with empty values
        metadata.update({"OpinionCluster": {}, "Docket": {}})
        if case_name:
            metadata["Docket"]["case_name"] = case_name
            metadata["OpinionCluster"]["case_name"] = case_name
        if docket_number:
            metadata["Docket"]["docket_number"] = normalize_dashes(
                docket_number
            )
        if lower_court:
            metadata["Docket"]["appeal_from_str"] = lower_court
        if lower_court_judge:
            metadata.update({"OriginatingCourtInformation": {}})
            metadata["OriginatingCourtInformation"]["assigned_to_str"] = (
                lower_court_judge
            )

        return metadata

    async def _download_backwards(self, dates: tuple[date, date]) -> None:
        """Page through the CTrack feed for a requested date window."""
        logger.info("Backscraping for range %s %s", *dates)
        start, end = dates
        page = 0
        while True:
            self.set_url(page, start, end)
            self.html = await self._download()
            results = self.html.get("_embedded", {}).get("results", [])
            if not results:
                break
            await self._process_html()
            page += 1
            if page >= self.html.get("page", {}).get("totalPages", 0):
                break
