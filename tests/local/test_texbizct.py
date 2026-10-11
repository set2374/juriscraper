import unittest

from lxml.html import fromstring

from juriscraper.opinions.united_states.state.texbizct import Site


class TexasBusinessCourtTest(unittest.IsolatedAsyncioTestCase):
    async def test_following_pdf_replaces_stale_heading_url(self):
        site = Site()
        site.html = fromstring(
            """
            <div class="panel-content">
              <h2><a href="/media/stale.pdf"
                title="24-BC11A-0021 Kassam v Dosani">
                Kassam v. Dosani, 2025 Tex. Bus. 25
              </a></h2>
              <p><a href="/media/current.pdf">Read the full opinion</a></p>
              <p><strong>Bullard, J. | June 30, 2025</strong></p>
              <ul><li>Denying a motion to sever.</li></ul>
            </div>
            """
        )

        await site._process_html()

        self.assertEqual(
            site.cases[0]["url"],
            "https://www.txcourts.gov/media/current.pdf",
        )
        self.assertEqual(site.cases[0]["judge"], "Bullard")
        self.assertEqual(site.cases[0]["date"], "June 30, 2025")

    async def test_heading_pdf_remains_fallback_without_replacement(self):
        site = Site()
        site.html = fromstring(
            """
            <div class="panel-content">
              <h2><a href="/media/original.pdf"
                title="24-BC01A-0002 BP Energy Company v Cox">
                BP Energy v. Cox, 2025 Tex. Bus. 27
              </a></h2>
              <p><strong>Bouressa, J. | July 16, 2025</strong></p>
              <ul><li>Granting an unopposed motion.</li></ul>
            </div>
            """
        )

        await site._process_html()

        self.assertEqual(
            site.cases[0]["url"],
            "https://www.txcourts.gov/media/original.pdf",
        )
        self.assertEqual(site.cases[0]["judge"], "Bouressa")
        self.assertEqual(site.cases[0]["date"], "July 16, 2025")


if __name__ == "__main__":
    unittest.main()
