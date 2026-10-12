import unittest
from datetime import date

from lxml import html

from juriscraper.opinions.united_states.state import alaska, alaskactapp

PAGE = """
<html><body>
  <h5><strong>Friday, October 9, 2026</strong></h5>
  <table class="table cms-opinion-table table-striped"><tbody>
    <tr>
      <td headers="table_header_document"><a href="/CMSPublic/UserControl/OpenOpinionDocument?q=published">PDF</a></td>
      <td headers="table_header_opinion">7833</td>
      <td headers="table_header_case">S19641</td>
      <td headers="table_header_title">Dash D. v. State of Alaska</td>
      <td headers="table_header_reference">600 P.3d 1</td>
    </tr>
  </tbody></table>
</body></html>
"""

ORDER_PAGE = """
<html><body>
  <h5><strong>Tuesday, September 29, 2026</strong></h5>
  <table class="table cms-opinion-table table-striped"><tbody>
    <tr>
      <td headers="table_header_document"><a href="/CMSPublic/UserControl/OpenBailDocument?q=order">PDF</a></td>
      <td headers="table_header_case">A15074</td>
      <td headers="table_header_title">Michael Hernandez v. State of Alaska</td>
    </tr>
  </tbody></table>
</body></html>
"""


class AlaskaNativeSourceTest(unittest.TestCase):
    def test_supreme_court_declares_every_native_decision_category(self):
        self.assertEqual(
            alaska.Site.source_pages,
            (
                ("Home/Opinions?isCOA=False", "Published"),
                ("Home/MOJOpinions?isCOA=False", "Unpublished"),
                ("Home/PublishedOrders?isCOA=False", "Published"),
            ),
        )

    def test_court_of_appeals_declares_every_native_decision_category(self):
        self.assertEqual(
            alaskactapp.Site.source_pages,
            (
                ("Home/Opinions?isCOA=True", "Published"),
                ("Home/MOJOpinions?isCOA=True", "Unpublished"),
                ("Home/SummaryDispositions?isCOA=True", "Unpublished"),
                ("Home/BailOrders", "Unpublished"),
                ("Home/CaseRelatedOrders", "Unpublished"),
            ),
        )

    def test_identity_encoding_uses_the_existing_httpx_proxy_path(self):
        site = alaska.Site()
        self.assertEqual(
            site.request["headers"]["Accept-Encoding"], "identity"
        )
        self.assertEqual(
            site.request["headers"]["User-Agent"], "Free Law Project"
        )
        self.assertFalse(site.use_urllib)

    def test_parses_published_and_nonprecedential_page_shapes(self):
        site = alaskactapp.Site()
        site.enable_test_mode()
        site._parse_page(html.fromstring(PAGE), "Published")
        site._parse_page(html.fromstring(ORDER_PAGE), "Unpublished")

        self.assertEqual(len(site.cases), 2)
        self.assertEqual(site.cases[0]["docket"], "S19641")
        self.assertEqual(site.cases[0]["citation"], "600 P.3d 1")
        self.assertEqual(site.cases[0]["status"], "Published")
        self.assertEqual(site.cases[1]["docket"], "A15074")
        self.assertEqual(site.cases[1]["citation"], "")
        self.assertEqual(site.cases[1]["status"], "Unpublished")
        self.assertIn("OpenBailDocument?q=order", site.cases[1]["url"])

    def test_filters_rows_outside_the_active_window(self):
        site = alaska.Site()
        site.start_date = date(2026, 10, 10)
        site.end_date = date(2026, 10, 11)
        site._parse_page(html.fromstring(PAGE), "Published")
        self.assertEqual(site.cases, [])

    def test_show_all_is_used_only_for_backscrape_urls(self):
        site = alaska.Site()
        current = site._source_url("Home/Opinions?isCOA=False")
        historical = site._source_url(
            "Home/Opinions?isCOA=False", show_all=True
        )
        self.assertNotIn("showAll", current)
        self.assertIn("showAll=True", historical)


if __name__ == "__main__":
    unittest.main()
