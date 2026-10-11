from .fisc import Site as FiscSite


class Site(FiscSite):
    """Foreign Intelligence Surveillance Court of Review opinions."""

    search_queries = (
        "FISCR opinion",
        "FISCR order",
        "FISC-R opinion",
        "FISC-R order",
    )
    court_markers = ("fiscr", "fisc-r", "fisc review", "court of review")
    excluded_markers = ()
    supplemental_records = (
        {
            "date": "2018-01-09",
            "date_filed_is_approximate": False,
            "docket": "FISCR 18-01",
            "name": "Order",
            "url": (
                "https://www.fisc.uscourts.gov/sites/default/files/"
                "FISCR%2018%2001%20WCB%20Order%20180109.pdf"
            ),
        },
        {
            "date": "2018-02-26",
            "date_filed_is_approximate": False,
            "docket": "FISCR 18-01",
            "name": "Order",
            "url": (
                "https://www.fisc.uscourts.gov/sites/default/files/"
                "FISCR%2018%2001%20WCB%20Order%20Feb%2026%202018.pdf"
            ),
        },
        {
            "date": "2018-03-16",
            "date_filed_is_approximate": False,
            "docket": "FISCR 18-01",
            "name": "FISCR 18-01 Opinion",
            "url": (
                "https://www.fisc.uscourts.gov/sites/default/files/"
                "FISCR%2018-01%20Opinion%20March%2016%202018.pdf"
            ),
        },
        {
            "date": "2020-03-13",
            "date_filed_is_approximate": False,
            "docket": "FISCR 20-01",
            "name": "Order to Show Cause",
            "url": (
                "https://www.fisc.uscourts.gov/sites/default/files/"
                "FISCR%2020%2001%20Order%20to%20Show%20Cause%20PJ%20JAC%20"
                "200313.pdf"
            ),
        },
        {
            "date": "2020-03-17",
            "date_filed_is_approximate": False,
            "docket": "FISCR 20-01",
            "name": "Order",
            "url": (
                "https://www.fisc.uscourts.gov/sites/default/files/"
                "FISCR%2020%2001%20Order%20March%2017%202020%20200410.pdf"
            ),
        },
        {
            "date": "2020-04-10",
            "date_filed_is_approximate": False,
            "docket": "FISCR 20-01",
            "name": "Order",
            "url": (
                "https://www.fisc.uscourts.gov/sites/default/files/"
                "FISCR%2020%2001%20Order%20April%2010%202020%20200410.pdf"
            ),
        },
        {
            "date": "2020-04-20",
            "date_filed_is_approximate": False,
            "docket": "FISCR 20-01",
            "name": "Order to Grant Relief",
            "url": (
                "https://www.fisc.uscourts.gov/sites/default/files/"
                "FISCR%2020%2001%20Order%20to%20Grant%20Relief%20200420.pdf"
            ),
        },
        {
            "date": "2020-04-24",
            "date_filed_is_approximate": False,
            "docket": "FISCR 20-01",
            "name": "Opinion",
            "url": (
                "https://www.fisc.uscourts.gov/sites/default/files/"
                "FISCR%2020%2001%20Opinion%20200424.pdf"
            ),
        },
        {
            "date": "2020-10-16",
            "date_filed_is_approximate": False,
            "docket": "FISCR Misc. 20-02",
            "name": "Order to Show Cause",
            "url": (
                "https://www.fisc.uscourts.gov/sites/default/files/"
                "FISCR%20Misc%2020%2002%20Order%20to%20Show%20Cause%20"
                "201016.pdf"
            ),
        },
        {
            "date": "2020-11-19",
            "date_filed_is_approximate": False,
            "docket": "FISCR Misc. 20-02",
            "name": "Opinion and Order",
            "url": (
                "https://www.fisc.uscourts.gov/sites/default/files/"
                "FISCR%20Misc%2020%2002%20Opinion%20and%20Order%20Nov%2019%20"
                "2020%20201119.pdf"
            ),
        },
    )

    def _legacy_record_belongs_to_court(
        self, docket: str, filename: str
    ) -> bool:
        normalized = f"{docket} {filename}".casefold()
        return any(marker in normalized for marker in self.court_markers)
