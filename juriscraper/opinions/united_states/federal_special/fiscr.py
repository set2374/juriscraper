from typing import ClassVar

from .fisc import Site as FiscSite


class Site(FiscSite):
    """Foreign Intelligence Surveillance Court of Review decisions."""

    search_queries: ClassVar[tuple[str, ...]] = (
        "FISCR opinion",
        "FISCR order",
        "FISC-R opinion",
        "FISC-R order",
    )
    court_markers: ClassVar[tuple[str, ...]] = (
        "fiscr",
        "fisc-r",
        "fisc review",
        "court of review",
    )
    excluded_markers = ()

    def _legacy_record_belongs_to_court(
        self, docket: str, filename: str
    ) -> bool:
        normalized = f"{docket} {filename}".casefold()
        return any(marker in normalized for marker in self.court_markers)
