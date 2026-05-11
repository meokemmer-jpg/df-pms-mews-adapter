"""Tests fuer MEWSConnector [CRUX-MK].

Welle-36 Pflicht-Tests fuer PMS-Adapter.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.mews_adapter import MEWSConnector, AdapterResponse, PMSAdapter


class TestMEWSConnectorSandbox:
    """Sandbox-Mode Default-Tests."""

    def test_connector_initializes_in_sandbox_by_default(self):
        c = MEWSConnector()
        assert c.sandbox_mode is True
        assert c.adapter_name == "mews-pms"
        assert c._connected is False

    def test_connect_sandbox_no_credentials(self):
        c = MEWSConnector(sandbox_mode=True)
        result = c.connect({})
        assert result is True
        assert c._connected is True

    def test_query_inventory_sandbox_returns_mock_data(self):
        c = MEWSConnector(sandbox_mode=True)
        c.connect({})
        inv = c.query_inventory("hildesheim", ("2026-06-01T14:00:00Z", "2026-06-02T11:00:00Z"))
        assert isinstance(inv, list)
        assert len(inv) == 3  # standard + deluxe + suite
        for room in inv:
            assert "hotel_id" in room
            assert "room_type" in room
            assert "available" in room
            assert "rate_eur" in room

    def test_query_inventory_unknown_hotel_returns_empty(self):
        c = MEWSConnector(sandbox_mode=True)
        c.connect({})
        inv = c.query_inventory("unknown-hotel", ("2026-06-01", "2026-06-02"))
        assert inv == []

    def test_book_room_sandbox_returns_mock_booking_id(self):
        c = MEWSConnector(sandbox_mode=True)
        c.connect({})
        booking_id = c.book_room(
            "hildesheim",
            "deluxe",
            {"name": "Test Guest", "email": "test@example.com"},
            ("2026-06-01", "2026-06-03"),
        )
        assert booking_id.startswith("mews-mock-")
        assert len(booking_id) > 10

    def test_cancel_booking_sandbox_success(self):
        c = MEWSConnector(sandbox_mode=True)
        c.connect({})
        result = c.cancel_booking("mews-mock-12345678")
        assert result is True

    def test_cancel_booking_sandbox_fail_prefix(self):
        c = MEWSConnector(sandbox_mode=True)
        c.connect({})
        result = c.cancel_booking("fail-mock-12345678")
        assert result is False

    def test_get_capabilities(self):
        c = MEWSConnector(sandbox_mode=True)
        caps = c.get_capabilities()
        assert caps["adapter_name"] == "mews-pms"
        assert caps["sandbox_mode"] is True
        assert "query_inventory" in caps["supported_operations"]
        assert "book_room" in caps["supported_operations"]
        assert caps["feature_flags"]["real_api"] is False
        assert caps["feature_flags"]["k17_pav"] is True


class TestMEWSConnectorRealMode:
    """Real-Mode-Tests (mit ENV-Var)."""

    def test_connect_real_mode_without_credentials_fails(self, monkeypatch):
        monkeypatch.setenv("DF_PMS_MEWS_REAL_ENABLED", "true")
        c = MEWSConnector()
        result = c.connect({})  # leere credentials
        assert result is False

    def test_book_room_real_mode_without_phronesis_ticket_fails(self, monkeypatch):
        monkeypatch.setenv("DF_PMS_MEWS_REAL_ENABLED", "true")
        monkeypatch.delenv("DF_PMS_MEWS_PHRONESIS_TICKET", raising=False)
        c = MEWSConnector(sandbox_mode=False)
        c._connected = True  # force connected for test
        booking_id = c.book_room(
            "hildesheim",
            "deluxe",
            {"name": "Test"},
            ("2026-06-01", "2026-06-03"),
        )
        assert booking_id == ""


class TestPMSAdapterInterface:
    """Test dass MEWSConnector PMSAdapter-Interface implementiert."""

    def test_mews_implements_pms_adapter(self):
        c = MEWSConnector(sandbox_mode=True)
        assert isinstance(c, PMSAdapter)

    def test_interface_has_all_required_methods(self):
        c = MEWSConnector(sandbox_mode=True)
        assert callable(c.connect)
        assert callable(c.query_inventory)
        assert callable(c.book_room)
        assert callable(c.cancel_booking)
        assert callable(c.get_capabilities)
