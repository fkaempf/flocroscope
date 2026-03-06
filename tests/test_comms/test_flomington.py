"""Tests for the Flomington placeholder module."""

from __future__ import annotations

import pytest

from flocroscope.comms.flomington import (
    FlomingtonClient,
    FlomingtonConfig,
    FlyCross,
    FlyStock,
)


class TestFlomingtonConfig:
    """Tests for FlomingtonConfig dataclass."""

    def test_defaults(self) -> None:
        """Default config is disabled with empty credentials."""
        cfg = FlomingtonConfig()
        assert cfg.enabled is False
        assert cfg.supabase_url == ""
        assert cfg.supabase_anon_key == ""
        assert cfg.auto_tag is True

    def test_custom_values(self) -> None:
        """Custom values are stored correctly."""
        cfg = FlomingtonConfig(
            enabled=True,
            supabase_url="https://example.supabase.co",
            user="Flo",
        )
        assert cfg.enabled is True
        assert cfg.user == "Flo"


class TestFlyStock:
    """Tests for FlyStock dataclass."""

    def test_defaults(self) -> None:
        """Default stock has empty fields."""
        stock = FlyStock()
        assert stock.stock_id == ""
        assert stock.genotype == ""
        assert stock.copies == 1
        assert stock.temperature == "25C"
        assert stock.genetic_tags == []

    def test_independent_tags(self) -> None:
        """Each stock gets its own tags list."""
        s1 = FlyStock()
        s2 = FlyStock()
        s1.genetic_tags.append("GAL4")
        assert len(s2.genetic_tags) == 0

    def test_custom_stock(self) -> None:
        """Custom stock values are stored."""
        stock = FlyStock(
            stock_id="abc12345",
            name="UAS-CsChrimson",
            genotype="w+; UAS-CsChrimson-mVenus",
            source="Bloomington",
            source_id="55135",
            genetic_tags=["UAS", "CsChrimson"],
        )
        assert stock.name == "UAS-CsChrimson"
        assert "CsChrimson" in stock.genetic_tags


class TestFlyCross:
    """Tests for FlyCross dataclass."""

    def test_defaults(self) -> None:
        """Default cross has empty fields."""
        cross = FlyCross()
        assert cross.cross_id == ""
        assert cross.status == "set up"
        assert cross.temperature == "25C"
        assert cross.experiment_type == ""

    def test_cross_lifecycle(self) -> None:
        """Cross with experiment type."""
        cross = FlyCross(
            cross_id="xyz98765",
            virgin_parent="GMR-GAL4",
            male_parent="UAS-CsChrimson",
            status="ripening",
            experiment_type="Optogenetics",
        )
        assert cross.experiment_type == "Optogenetics"
        assert cross.status == "ripening"


class TestFlomingtonClient:
    """Tests for FlomingtonClient placeholder."""

    def test_not_connected(self) -> None:
        """Client starts disconnected."""
        client = FlomingtonClient(FlomingtonConfig())
        assert client.connected is False

    def test_connect_without_url(self) -> None:
        """Connect returns False without a URL."""
        client = FlomingtonClient(FlomingtonConfig())
        assert client.connect() is False
        assert client.connected is False

    def test_get_stock_returns_none(self) -> None:
        """get_stock returns None (placeholder)."""
        client = FlomingtonClient(FlomingtonConfig())
        assert client.get_stock("abc") is None

    def test_get_cross_returns_none(self) -> None:
        """get_cross returns None (placeholder)."""
        client = FlomingtonClient(FlomingtonConfig())
        assert client.get_cross("xyz") is None

    def test_search_stocks_returns_empty(self) -> None:
        """search_stocks returns empty list (placeholder)."""
        client = FlomingtonClient(FlomingtonConfig())
        assert client.search_stocks("GAL4") == []

    def test_get_crosses_for_experiment(self) -> None:
        """get_crosses_for_experiment returns empty (placeholder)."""
        client = FlomingtonClient(FlomingtonConfig())
        assert client.get_crosses_for_experiment("2P") == []

    def test_tag_session_returns_false(self) -> None:
        """tag_session returns False (placeholder)."""
        client = FlomingtonClient(FlomingtonConfig())
        assert client.tag_session("s1", stock_id="abc") is False

    def test_push_results_returns_false(self) -> None:
        """push_results returns False (placeholder)."""
        client = FlomingtonClient(FlomingtonConfig())
        assert client.push_results("s1", {}) is False

    def test_disconnect(self) -> None:
        """Disconnect is a no-op."""
        client = FlomingtonClient(FlomingtonConfig())
        client.disconnect()  # should not raise
        assert client.connected is False
