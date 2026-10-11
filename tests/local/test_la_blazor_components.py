from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from juriscraper.opinions.united_states.state.la import Site


class LouisianaBlazorComponentTest(IsolatedAsyncioTestCase):
    async def test_shell_preserves_keyed_component_descriptor(self):
        shell = """
        <!--Blazor:{"type":"server","prerenderId":"pre-0","key":
        {"locationHash":"hash-0","formattedComponentKey":""},
        "sequence":0,"descriptor":"descriptor-0"}-->
        <!--Blazor:{"prerenderId":"pre-0"}-->
        <!--Blazor:{"type":"server","key":
        {"locationHash":"hash-1","formattedComponentKey":""},
        "sequence":1,"descriptor":"descriptor-1"}-->
        <!--Blazor-Server-Component-State:application-state-->
        """
        site = Site()
        site._get_with_retries = AsyncMock(return_value=shell)

        markers, application_state = await site._get_blazor_shell(
            "https://www.lasc.org/Opinions?p=2026-037"
        )

        self.assertEqual(application_state, "application-state")
        self.assertEqual(
            markers,
            [
                {
                    "type": "server",
                    "prerenderId": "pre-0",
                    "key": {
                        "locationHash": "hash-0",
                        "formattedComponentKey": "",
                    },
                    "sequence": 0,
                    "descriptor": "descriptor-0",
                    "uniqueId": 0,
                },
                {
                    "type": "server",
                    "key": {
                        "locationHash": "hash-1",
                        "formattedComponentKey": "",
                    },
                    "sequence": 1,
                    "descriptor": "descriptor-1",
                    "uniqueId": 1,
                },
            ],
        )
