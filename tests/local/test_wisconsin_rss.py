import unittest
from datetime import date

import httpx

from juriscraper.opinions.united_states.state import wis, wisctapp


def rss(title: str, link: str) -> str:
    published = date.today().strftime("%b %d, %Y")
    return f"""<?xml version="1.0"?>
    <rss version="2.0"><channel><item>
      <title>{title}</title><link>{link}</link>
      <pubDate>{published}</pubDate><guid>{title}-{published}</guid>
    </item></channel></rss>"""


async def parse_with_detail(site, feed: str, detail: str):
    requested = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        body = feed if "rss/" in request.url.path else detail
        return httpx.Response(200, text=body, request=request)

    site.request["session"] = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )
    async with site:
        await site.parse()
    return requested


class WisconsinRssTest(unittest.IsolatedAsyncioTestCase):
    async def test_supreme_court_rss_resolves_pdf_row(self):
        site = wis.Site()
        feed = rss(
            "2026AP000001 - State v. Example",
            "http://www.wicourts.gov/supreme/scopin.jsp?docket_number=2026AP000001",
        )
        detail = """<table><tbody><tr>
          <td>10/08/2026</td><td>2026AP000001</td><td>State v. Example</td>
          <td><input name="/sc/opinion/DisplayDocument.pdf?content=pdf&amp;seqNo=1" /></td>
        </tr></tbody></table>"""

        requested = await parse_with_detail(site, feed, detail)

        self.assertEqual(
            requested[0], "https://www.wicourts.gov/rss/scopin.jsp"
        )
        self.assertTrue(
            requested[1].startswith(
                "https://www.wicourts.gov/supreme/scopin.jsp"
            )
        )
        self.assertEqual(
            site.download_urls,
            (
                "https://www.wicourts.gov/sc/opinion/DisplayDocument.pdf?content=pdf&seqNo=1",
            ),
        )
        self.assertEqual(site.docket_numbers, ("2026AP000001",))

    async def test_appeals_rss_preserves_status_and_lower_court(self):
        site = wisctapp.Site()
        feed = rss(
            "2026AP000002 - County v. Example",
            "http://www.wicourts.gov/other/appeals/caopin.jsp?docket_number=2026AP000002",
        )
        detail = """<table><tbody><tr>
          <td>10/08/2026</td><td>2026AP000002</td>
          <td>County v. Example<br/>Recommended for Publication</td>
          <td>II</td><td>Dane</td>
          <td><input name="/ca/opinion/DisplayDocument.pdf?content=pdf&amp;seqNo=2" /></td>
        </tr></tbody></table>"""

        await parse_with_detail(site, feed, detail)

        self.assertEqual(
            site.download_urls,
            (
                "https://www.wicourts.gov/ca/opinion/DisplayDocument.pdf?content=pdf&seqNo=2",
            ),
        )
        self.assertEqual(site.precedential_statuses, ("Published",))
        self.assertEqual(
            site.lower_courts,
            ("Wisconsin Circuit Court, Dane County",),
        )
