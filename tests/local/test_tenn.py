import unittest

from lxml.html import fromstring

from juriscraper.opinions.united_states.state.tenn_workers_comp import (
    Site as TennesseeWorkersCompSite,
)
from juriscraper.opinions.united_states.state.tennctapp import Site


class TennesseePendingDocumentTest(unittest.TestCase):
    def test_workers_compensation_uses_its_native_court_identity(self):
        site = TennesseeWorkersCompSite()

        self.assertEqual(site.court_id, "tennworkcompapp")

    def test_row_without_document_url_is_deferred(self):
        site = Site()
        site.html = fromstring(
            """
            <table>
              <tr>
                <td class="views-field-field-opinions-date-filed">10/10/2026</td>
                <td class="views-field-field-opinions-case-number">
                  <a href="https://www.tncourts.gov/courts/court-appeals/opinions">
                    Pending opinion
                  </a>
                </td>
              </tr>
              <tr>
                <td class="views-field-field-opinions-date-filed">10/09/2026</td>
                <td class="views-field-field-opinions-case-number">
                  <a href="/opinions/published.pdf">Published opinion</a>
                  <p>E2026-00001-COA-R3-CV</p>
                  <p>Authoring Judge: Jane Doe, Judge</p>
                  <p>A published decision.</p>
                </td>
              </tr>
            </table>
            """
        )

        with self.assertLogs(level="WARNING") as logs:
            site._process_html()

        self.assertEqual(len(site.cases), 1)
        self.assertEqual(site.cases[0]["name"], "Published opinion")
        self.assertEqual(site.cases[0]["url"], "/opinions/published.pdf")
        self.assertIn("without a document URL", " ".join(logs.output))


if __name__ == "__main__":
    unittest.main()
