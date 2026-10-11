from unittest.mock import patch

from juriscraper.opinions.united_states.state import (
    kan_p,
    lactapp_3,
    ncbizct,
)


def test_official_sources_use_proxy_aware_native_client():
    """The urllib path ignores configured SOCKS egress and gets publisher 403s."""
    for site_class in (kan_p.Site, lactapp_3.Site, ncbizct.Site):
        assert site_class().use_urllib is False


def test_kansas_and_louisiana_third_circuit_use_http11():
    """Both publishers return a Cloudflare 403 when the client negotiates HTTP/2."""
    for site_class in (kan_p.Site, lactapp_3.Site):
        with patch("juriscraper.AbstractSite.httpx.AsyncClient") as client:
            site_class()
        assert client.call_args.kwargs["http2"] is False
