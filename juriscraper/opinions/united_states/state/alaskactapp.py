"""Scraper for the Alaska Court of Appeals.
CourtID: alaskactapp
Court Short Name: Alaska Ct. App.

The Court of Appeals shares the Alaska Court System native publication surface
with the Supreme Court. See alaska.py.
"""

from juriscraper.opinions.united_states.state import alaska


class Site(alaska.Site):
    source_pages: tuple[tuple[str, str], ...] = (
        ("Home/Opinions?isCOA=True", "Published"),
        ("Home/MOJOpinions?isCOA=True", "Unpublished"),
        ("Home/SummaryDispositions?isCOA=True", "Unpublished"),
        ("Home/BailOrders", "Unpublished"),
        ("Home/CaseRelatedOrders", "Unpublished"),
    )
