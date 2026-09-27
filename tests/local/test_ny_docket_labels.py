import unittest

from lxml.html import fromstring

from juriscraper.opinions.united_states.state.ny import (
    clean_repeated_docket_labels,
)
from juriscraper.opinions.united_states.state.nyappdiv_1st import Site


class NewYorkDocketLabelsTest(unittest.TestCase):
    def test_repeated_labels_are_removed_from_search_and_opinion_metadata(self):
        docket = (
            "Index No. Index No. 652044/14 Appeal No. 12147 "
            "Case No. Case No. 2019-05390"
        )
        expected = "Index No. 652044/14 Appeal No. 12147 Case No. 2019-05390"
        site = Site()
        cells = [
            "Case", "10/22/2020", docket, "", "187 AD3d 623", "",
            '<a href="/opinion"><span>2020 NY Slip Op 06039</span></a>',
            "", "",
        ]
        site.html = fromstring(
            '<div><table class="table"><tbody><tr>'
            + "".join(f"<td>{cell}</td>" for cell in cells)
            + "</tr></tbody></table></div>"
        )

        site._process_html()
        self.assertEqual(site.cases[0]["docket"], expected)

        metadata = site.extract_from_text(f"<br>{docket}<br>")
        self.assertEqual(metadata["Docket"]["docket_number"], expected)
        self.assertEqual(
            clean_repeated_docket_labels("Case No. 2020-1 Case No. 2020-2"),
            "Case No. 2020-1 Case No. 2020-2",
        )
        self.assertEqual(
            clean_repeated_docket_labels("Index No. Index No. Index No. 12/24"),
            "Index No. 12/24",
        )


if __name__ == "__main__":
    unittest.main()
