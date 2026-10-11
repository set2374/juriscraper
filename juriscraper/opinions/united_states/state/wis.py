import re
from datetime import date, datetime, timedelta
from urllib.parse import urlencode, urljoin

import feedparser
import httpx
from typing_extensions import override

from juriscraper.AbstractSite import logger
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    days_interval = 15
    first_opinion_date = datetime(1995, 6, 1).date()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.base_url = "https://www.wicourts.gov/supreme/scopin.jsp"
        self.feed_url = "https://www.wicourts.gov/rss/scopin.jsp"
        self.status = "Published"
        self.set_url()
        self.cite_regex = r"20\d{2}\sWI\s\d+"
        self.make_backscrape_iterable(kwargs)

    def set_url(
        self, start: date | None = None, end: date | None = None
    ) -> None:
        """Sets URL with appropriate query parameters

        :param start: start date
        :param end: end date
        :return None
        """
        if not start:
            self.url = self.feed_url
            return

        start = start.strftime("%m-%d-%Y")
        end = end.strftime("%m-%d-%Y")

        params = {
            "range": "None",
            "begin_date": start,
            "end_date": end,
            "sortBy": "date",
            "Submit": "Search",
        }
        self.url = f"{self.base_url}?{urlencode(params)}"

    @override
    async def _process_html(self) -> None:
        """Process the HTML from wisconsin

        :return: None
        """
        html = self.html
        if html is None:
            return
        if html.xpath(".//item"):
            await self._process_rss()
            return
        self._process_opinion_rows(html)

    async def _process_rss(self) -> None:
        """Resolve current RSS entries to the court's PDF result rows.

        The court's date-range search is blocked for automated clients, while
        its documented RSS feeds remain available. RSS entries point to a
        one-docket result page rather than the opinion PDF, so retain the
        existing row parser and resolve only entries in the normal current
        scrape window.
        """
        cutoff = date.today() - timedelta(days=self.days_interval)
        response = self.request["response"]
        assert isinstance(response, httpx.Response)
        feed = feedparser.parse(response.content)
        detail_urls = []
        for item in feed.entries:
            if item.get("published_parsed") is not None:
                published = date(*item.published_parsed[:3])
            else:
                try:
                    published = datetime.strptime(
                        item.get("published", "").strip(), "%b %d, %Y"
                    ).date()
                except ValueError:
                    published = None
            if published is None:
                logger.warning("Skipping RSS item with no publication date")
                continue
            if published < cutoff:
                continue
            detail_urls.append(item.link.replace("http://", "https://", 1))

        for detail_url in dict.fromkeys(detail_urls):
            logger.info("Resolving Wisconsin RSS item: %s", detail_url)
            response = await self.request["session"].get(
                detail_url,
                headers=self.request["headers"],
                timeout=60,
            )
            response.raise_for_status()
            self._process_opinion_rows(self._make_html_tree(response.text))

    def _process_opinion_rows(self, html) -> None:
        """Parse opinion rows from a date search or RSS detail response."""
        for row in html.xpath(".//table/tbody/tr | self::table/tbody/tr"):
            date, docket, caption, link = row.xpath("./td")
            self.cases.append(
                {
                    "date": date.text,
                    "name": caption.text,
                    "url": urljoin(
                        "https://www.wicourts.gov",
                        link.xpath("./input")[0].name,
                    ),
                    "docket": docket.text,
                }
            )

    def extract_from_text(self, scraped_text: str) -> dict:
        """Extract citation from text

        :param scraped_text: Text of scraped content
        :return: date filed
        """
        first_line = scraped_text[:100].splitlines()[0]
        if match := re.search(self.cite_regex, first_line):
            return {"Citation": match.group(0)}

        return {}

    async def _download_backwards(self, dates: tuple[date, date]) -> None:
        """Set date range from backscraping args and scrape

        :param dates: (start_date, end_date) tuple
        :return None
        """
        logger.info("Backscraping for range %s %s", *dates)
        self.set_url(*dates)
        self.html = await self._download()
        await self._process_html()
