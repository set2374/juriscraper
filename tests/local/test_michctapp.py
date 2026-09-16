import unittest

from juriscraper.opinions.united_states.state.michctapp import Site


class MichiganCourtOfAppealsTest(unittest.IsolatedAsyncioTestCase):
    async def test_numbered_duplicate_majority_version_is_skipped(self):
        base_item = {
            "courts": ["OAKLAND CIRCUIT COURT"],
            "decision": "Affirmed",
            "filingDate": "2026-08-25T04:00:00+00:00",
            "title": (
                "COA 370206 ESTATE OF ELIZABETH JORDAN V HEART AND "
                "VASCULAR CONSULTANTS PLLC Opinion - Per Curiam - "
                "Unpublished 8/25/2026"
            ),
        }
        site = Site()
        site.html = {
            "searchItems": [
                {
                    **base_item,
                    "documentUrl": "/version-a/opinions/370206.opn2.pdf",
                },
                {
                    **base_item,
                    "documentUrl": "/version-b/opinions/370206.opn.pdf",
                },
            ]
        }

        await site._process_html()

        self.assertEqual(len(site.cases), 1)
        self.assertTrue(site.cases[0]["url"].endswith("370206.opn2.pdf"))
