""" Unit tests for pricing module

"""
import os
from datetime import datetime

import pytest
from requests import JSONDecodeError
from telliot_core.apps.telliot_config import TelliotConfig

from telliot_feeds.sources.price.spot import coingecko
from telliot_feeds.sources.price.spot.bittrex import BittrexSpotPriceService
from telliot_feeds.sources.price.spot.coinbase import CoinbaseSpotPriceService
from telliot_feeds.sources.price.spot.coingecko import CoinGeckoSpotPriceService
from telliot_feeds.sources.price.spot.gemini import GeminiSpotPriceService
from telliot_feeds.sources.price.spot.nomics import NomicsSpotPriceService
from telliot_feeds.sources.price.spot.pancakeswap import (
    PancakeswapPriceService,
)
from telliot_feeds.sources.price.spot.pulsechain_subgraph import PulsechainSupgraphService
from telliot_feeds.sources.price.spot.uniswapV3 import UniswapV3PriceService


service = {
    "coinbase": CoinbaseSpotPriceService(),
    "coingecko": CoinGeckoSpotPriceService(),
    "bittrex": BittrexSpotPriceService(),
    "gemini": GeminiSpotPriceService(),
    "nomics": NomicsSpotPriceService(),
    "pancakeswap": PancakeswapPriceService(),
    "uniswapV3": UniswapV3PriceService(),
    "pulsechain-subgraph": PulsechainSupgraphService(),
}


async def get_price(asset, currency, s, timeout=10.0):
    """Helper function for retrieving prices."""
    s.timeout = timeout
    v, t = await s.get_price(asset, currency)
    return v, t


def validate_price(v, t):
    """Check types and price anomalies."""
    assert v is not None
    assert isinstance(v, float)
    assert v > 0
    assert isinstance(t, datetime)
    print(v)
    print(t)


@pytest.fixture(scope="module")
def nomics_key():
    key = TelliotConfig().api_keys.find(name="nomics")[0].key

    if not key and "NOMICS_KEY" in os.environ:
        key = os.environ["NOMICS_KEY"]

    return key


@pytest.fixture(scope="module")
def coinmarketcap_key():
    key = TelliotConfig().api_keys.find(name="coinmarketcap")[0].key

    if not key and "COINMARKETCAP_KEY" in os.environ:
        key = os.environ["COINMARKETCAP_KEY"]

    return key


@pytest.mark.asyncio
async def test_coinbase():
    """Test retrieving from Coinbase price source."""
    v, t = await get_price("btc", "usd", service["coinbase"])
    validate_price(v, t)

    v, t = await get_price("trb", "usd", service["coinbase"])
    validate_price(v, t)


@pytest.mark.asyncio
async def test_coingecko():
    """Test retrieving from Coingecko price source."""
    v, t = await get_price("btc", "usd", service["coingecko"])
    validate_price(v, t)


@pytest.mark.asyncio
async def test_nomics(nomics_key):
    """Test retrieving from Nomics price source."""
    if nomics_key:
        v, t = await get_price("btc", "usd", service["nomics"])
        validate_price(v, t)
    else:
        print("No Nomics API key ")


@pytest.mark.asyncio
async def test_coinmarketcap(coinmarketcap_key):
    """Test retrieving from CoinMarketCap price source."""
    if coinmarketcap_key:
        v, t = await get_price("bct", "usd", service["coinmarketcap"])
        validate_price(v, t)
    else:
        print("No CoinMarketCap API key ")


@pytest.mark.asyncio
async def test_bittrex(caplog):
    """Test retrieving from Bittrex price source."""
    v, t = await get_price("btc", "usd", service["bittrex"])

    if "Bittrex API rate limit exceeded" in caplog.text:
        assert v is None
        assert t is None
    else:
        validate_price(v, t)


@pytest.mark.asyncio
async def test_gemini(caplog):
    """Test retrieving from Gemini price source."""
    v, t = await get_price("btc", "usd", service["gemini"])

    if "Gemini API rate limit exceeded" in caplog.text:
        assert v is None
        assert t is None
    else:
        validate_price(v, t)


@pytest.mark.asyncio
async def test_uniswap_usd(caplog):
    """Test retrieving from UniswapV3 price source in USD."""
    v, t = await get_price("fuse", "usd", service["uniswapV3"])
    if type(v) == float:
        validate_price(v, t)
    else:
        assert "Uniswap API not included, because price response is 0" in caplog.records[0].msg


@pytest.mark.asyncio
async def test_uniswap_timeout():
    """Test retrieving from UniswapV3 price source in USD."""
    v, t = await get_price("fuse", "usd", service["uniswapV3"], 0.05)
    assert v is None
    assert t is None


@pytest.mark.asyncio
async def test_uniswap_eth(caplog):
    """Test retrieving from UniswapV3 price source in ETH."""
    v, t = await get_price("fuse", "eth", service["uniswapV3"])
    if type(v) == float:
        validate_price(v, t)
    else:
        assert "Uniswap API not included, because price response is 0" in caplog.records[0].msg


@pytest.mark.asyncio
async def test_uniswap_eth_usd(caplog):
    """Test retrieving from UniswapV3 price source for Eth in USD."""
    v, t = await get_price("eth", "usd", service["uniswapV3"])
    if type(v) == float:
        validate_price(v, t)
    else:
        assert "Uniswap API not included, because price response is 0" in caplog.records[0].msg


@pytest.mark.asyncio
async def test_pancakeswap_usd():
    """Test retrieving from Pancakeswap price source in USD."""
    v, t = await get_price("fuse", "usd", service["pancakeswap"])
    validate_price(v, t)


@pytest.mark.asyncio
async def test_pancakeswap_bnb():
    """Test retrieving from Pancakeswap price source in BNB."""
    v, t = await get_price("fuse", "bnb", service["pancakeswap"])
    validate_price(v, t)


@pytest.mark.asyncio
async def test_pulsechain_subgraph():
    """Test retreiving from Pulsechain Subgraph PLS/USD feed"""
    v, t = await get_price("pls", "usd", service["pulsechain-subgraph"])
    validate_price(v, t)


@pytest.mark.asyncio
async def test_coingecko_price_service_rate_limit(caplog):
    def mock_get_url(self, url):
        return {
            "error": "<class 'requests.exceptions.JSONDecodeError'>",
            "exception": JSONDecodeError(
                "Expecting value",
                '<!DOCTYPE html>\n<!--[if lt IE 7]> <html class="no-js ie6 oldie" lang="en-US"> <![endif]-->\n<!--[if IE 7]>    <html class="no-js ie7 oldie" lang="en-US"> <![endif]-->\n<!--[if IE 8]>    <html class="no-js ie8 oldie" lang="en-US"> <![endif]-->\n<!--[if gt IE 8]><!--> <html class="no-js" lang="en-US"> <!--<![endif]-->\n<head>\n<title>Access denied | api.coingecko.com used Cloudflare to restrict access</title>\n<meta charset="UTF-8" />\n<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />\n<meta http-equiv="X-UA-Compatible" content="IE=Edge,chrome=1" />\n<meta name="robots" content="noindex, nofollow" />\n<meta name="viewport" content="width=device-width,initial-scale=1" />\n<link rel="stylesheet" id="cf_styles-css" href="/cdn-cgi/styles/main.css" type="text/css" media="screen,projection" />\n\n\n<script type="text/javascript">\n(function(){if(document.addEventListener&&window.XMLHttpRequest&&JSON&&JSON.stringify){var e=function(a){var c=document.getElementById("error-feedback-survey"),d=document.getElementById("error-feedback-success"),b=new XMLHttpRequest;a={event:"feedback clicked",properties:{errorCode:1015,helpful:a,version:1}};b.open("POST","https://sparrow.cloudflare.com/api/v1/event");b.setRequestHeader("Content-Type","application/json");b.setRequestHeader("Sparrow-Source-Key","c771f0e4b54944bebf4261d44bd79a1e");\nb.send(JSON.stringify(a));c.classList.add("feedback-hidden");d.classList.remove("feedback-hidden")};document.addEventListener("DOMContentLoaded",function(){var a=document.getElementById("error-feedback"),c=document.getElementById("feedback-button-yes"),d=document.getElementById("feedback-button-no");"classList"in a&&(a.classList.remove("feedback-hidden"),c.addEventListener("click",function(){e(!0)}),d.addEventListener("click",function(){e(!1)}))})}})();\n</script>\n\n<script defer src="https://api.radar.cloudflare.com/beacon.js"></script>\n</head>\n<body>\n  <div id="cf-wrapper">\n    <div class="cf-alert cf-alert-error cf-cookie-error hidden" id="cookie-alert" data-translate="enable_cookies">Please enable cookies.</div>\n    <div id="cf-error-details" class="p-0">\n      <header class="mx-auto pt-10 lg:pt-6 lg:px-8 w-240 lg:w-full mb-15 antialiased">\n         <h1 class="inline-block md:block mr-2 md:mb-2 font-light text-60 md:text-3xl text-black-dark leading-tight">\n           <span data-translate="error">Error</span>\n           <span>1015</span>\n         </h1>\n         <span class="inline-block md:block heading-ray-id font-mono text-15 lg:text-sm lg:leading-relaxed">Ray ID: 6fe62dfef8545773 &bull;</span>\n         <span class="inline-block md:block heading-ray-id font-mono text-15 lg:text-sm lg:leading-relaxed">2022-04-19 14:02:44 UTC</span>\n        <h2 class="text-gray-600 leading-1.3 text-3xl lg:text-2xl font-light">You are being rate limited</h2>\n      </header>\n\n      <section class="w-240 lg:w-full mx-auto mb-8 lg:px-8">\n          <div id="what-happened-section" class="w-1/2 md:w-full">\n            <h2 class="text-3xl leading-tight font-normal mb-4 text-black-dark antialiased" data-translate="what_happened">What happened?</h2>\n            <p>The owner of this website (api.coingecko.com) has banned you temporarily from accessing this website.</p>\n            \n          </div>\n\n          \n      </section>\n\n      <div class="feedback-hidden py-8 text-center" id="error-feedback">\n    <div id="error-feedback-survey" class="footer-line-wrapper">\n        Was this page helpful?\n        <button class="border border-solid bg-white cf-button cursor-pointer ml-4 px-4 py-2 rounded" id="feedback-button-yes" type="button">Yes</button>\n        <button class="border border-solid bg-white cf-button cursor-pointer ml-4 px-4 py-2 rounded" id="feedback-button-no" type="button">No</button>\n    </div>\n    <div class="feedback-success feedback-hidden" id="error-feedback-success">\n        Thank you for your feedback!\n    </div>\n</div>\n\n\n      <div class="cf-error-footer cf-wrapper w-240 lg:w-full py-10 sm:py-4 sm:px-8 mx-auto text-center sm:text-left border-solid border-0 border-t border-gray-300">\n  <p class="text-13">\n    <span class="cf-footer-item sm:block sm:mb-1">Cloudflare Ray ID: <strong class="font-semibold">6fe62dfef8545773</strong></span>\n    <span class="cf-footer-separator sm:hidden">&bull;</span>\n    <span class="cf-footer-item sm:block sm:mb-1"><span>Your IP</span>: 13.58.215.91</span>\n    <span class="cf-footer-separator sm:hidden">&bull;</span>\n    <span class="cf-footer-item sm:block sm:mb-1"><span>Performance &amp; security by</span> <a rel="noopener noreferrer" href="https://www.cloudflare.com/5xx-error-landing" id="brand_link" target="_blank">Cloudflare</a></span>\n    \n  </p>\n</div><!-- /.error-footer -->\n\n\n    </div><!-- /#cf-error-details -->\n  </div><!-- /#cf-wrapper -->\n\n  <script type="text/javascript">\n  window._cf_translation = {};\n  \n  \n</script>\n\n</body>\n</html>\n',  # noqa: E501
            ),
        }

    coingecko.WebPriceService.get_url = mock_get_url
    ps = CoinGeckoSpotPriceService(timeout=0.5)
    v, dt = await ps.get_price("trb", "usd")

    assert v is None
    assert dt is None
    assert "CoinGecko API rate limit exceeded" in caplog.text


@pytest.mark.asyncio
async def test_failed_price_service_request():
    """Assert web price service catches failed requests"""

    invalid_token_ticker = "abcxyz"

    v, t = await get_price(invalid_token_ticker, "usd", service["gemini"])

    assert v is None
    assert t is None
