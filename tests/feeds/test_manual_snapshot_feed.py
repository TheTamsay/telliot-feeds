from unittest import mock

import pytest

from telliot_feeds.feeds.snapshot_feed import snapshot_manual_feed
from telliot_feeds.utils.log import get_logger

logger = get_logger(__name__)


@pytest.mark.asyncio
async def test_valid_user_nput(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda: "n")
    val, _ = await snapshot_manual_feed.source.fetch_new_datapoint()
    assert isinstance(val, bool)
    assert val is False

    monkeypatch.setattr("builtins.input", lambda: "y")
    (val, _) = await snapshot_manual_feed.source.fetch_new_datapoint()
    assert isinstance(val, bool)
    assert val is True


@pytest.mark.asyncio
async def test_bad_user_input():
    with mock.patch("builtins.input", side_effect=["", "not a bool", "y", ""]):
        (val, _) = await snapshot_manual_feed.source.fetch_new_datapoint()
        assert type(val) is bool
        assert val is True
