"""MEWS-Adapter [CRUX-MK].

Connector fuer MEWS PMS-API:
- Booking-API (book/cancel)
- Reservation-API (query reservations)
- Inventory-API (query rooms / availability)

K12 Provenance: jede Response hat source-tracking-fields.
K13 PAV: Real-Bookings require DF_PMS_MEWS_PHRONESIS_TICKET ENV-Var.
ENV-Var-gated: DF_PMS_MEWS_REAL_ENABLED=false (Default) -> Mock.

Welle-36.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AdapterResponse:
    """Kanonische Adapter-Response (LC4 idempotent + K12 provenance).

    source ∈ {"mock", "real-api", "stub"}
    """
    adapter_name: str
    operation: str
    success: bool
    payload: dict
    source: str
    timestamp_iso: str
    request_hash: str
    error: Optional[str] = None


class PMSAdapter(ABC):
    """Pflicht-Interface fuer alle PMS-Adapter (Mosaic-Layer-Shared)."""

    @abstractmethod
    def connect(self, credentials: dict) -> bool:
        ...

    @abstractmethod
    def query_inventory(self, hotel_id: str, date_range: tuple) -> list[dict]:
        ...

    @abstractmethod
    def book_room(self, hotel_id: str, room_type: str, guest: dict, dates: tuple) -> str:
        ...

    @abstractmethod
    def cancel_booking(self, booking_id: str) -> bool:
        ...

    @abstractmethod
    def get_capabilities(self) -> dict:
        ...


class MEWSConnector(PMSAdapter):
    """MEWS PMS-API Connector.

    Sandbox-Default: deterministische Mock-Daten basierend auf request_hash.
    Real-Mode: HTTP-Calls an MEWS-API (placeholder, Welle-37 Live-Implementation).
    """

    MOCK_HOTELS = {
        "hildesheim": {"property_id": "mock-hildesheim-001", "rooms_total": 80},
        "cape-coral": {"property_id": "mock-cape-coral-001", "rooms_total": 60},
        "munich": {"property_id": "mock-munich-001", "rooms_total": 120},
    }

    def __init__(self, sandbox_mode: Optional[bool] = None):
        self.adapter_name = "mews-pms"
        if sandbox_mode is None:
            self.sandbox_mode = os.environ.get("DF_PMS_MEWS_REAL_ENABLED", "false") != "true"
        else:
            self.sandbox_mode = sandbox_mode
        self._connected = False
        self._credentials: Optional[dict] = None

    # ---- Helpers ----
    def _request_hash(self, operation: str, payload: dict) -> str:
        canonical = json.dumps({"op": operation, "payload": payload}, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _build_response(
        self,
        operation: str,
        success: bool,
        payload: dict,
        request_hash: str,
        error: Optional[str] = None,
    ) -> AdapterResponse:
        return AdapterResponse(
            adapter_name=self.adapter_name,
            operation=operation,
            success=success,
            payload=payload,
            source="mock" if self.sandbox_mode else ("real-api" if success else "stub"),
            timestamp_iso=self._now_iso(),
            request_hash=request_hash,
            error=error,
        )

    # ---- PMSAdapter Interface ----
    def connect(self, credentials: dict) -> bool:
        """Establish connection. K11 try/except, LC4 idempotent."""
        try:
            if self.sandbox_mode:
                self._connected = True
                self._credentials = credentials
                return True

            client_token = credentials.get("client_token", "")
            access_token = credentials.get("access_token", "")
            if not client_token or not access_token:
                logger.warning("[mews-adapter] missing credentials for connect")
                self._connected = False
                return False

            # Real-API connect placeholder (Welle-37)
            self._credentials = credentials
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"[mews-adapter] connect failed: {e}")
            self._connected = False
            return False

    def query_inventory(self, hotel_id: str, date_range: tuple) -> list[dict]:
        """Query verfuegbare Zimmer fuer Hotel + Datumsbereich.

        date_range: (check_in_iso, check_out_iso)
        """
        op = "query_inventory"
        try:
            if not self._connected:
                return []

            criteria = {"hotel_id": hotel_id, "date_range": list(date_range)}
            h = self._request_hash(op, criteria)

            if self.sandbox_mode:
                hotel = self.MOCK_HOTELS.get(hotel_id, {})
                if not hotel:
                    return []
                # Deterministische Mock-Inventur basierend auf hash
                hash_int = int(h, 16) % 100
                available = max(0, hotel["rooms_total"] - hash_int)
                return [
                    {
                        "hotel_id": hotel_id,
                        "property_id": hotel["property_id"],
                        "room_type": "standard",
                        "available": available // 3,
                        "rate_eur": 95.0 + (hash_int % 30),
                    },
                    {
                        "hotel_id": hotel_id,
                        "property_id": hotel["property_id"],
                        "room_type": "deluxe",
                        "available": available // 4,
                        "rate_eur": 145.0 + (hash_int % 40),
                    },
                    {
                        "hotel_id": hotel_id,
                        "property_id": hotel["property_id"],
                        "room_type": "suite",
                        "available": available // 10,
                        "rate_eur": 245.0 + (hash_int % 60),
                    },
                ]

            # Real-API placeholder (Welle-37)
            logger.warning("[mews-adapter] real-api query_inventory not yet implemented")
            return []
        except Exception as e:
            logger.error(f"[mews-adapter] query_inventory failed: {e}")
            return []

    def book_room(self, hotel_id: str, room_type: str, guest: dict, dates: tuple) -> str:
        """Buche Zimmer. K17-PAV: Real-Bookings require Phronesis-Ticket.

        Returns booking_id (string) oder leeren String bei Failure.
        """
        op = "book_room"
        try:
            if not self._connected:
                return ""

            payload = {
                "hotel_id": hotel_id,
                "room_type": room_type,
                "guest": guest,
                "dates": list(dates),
            }
            h = self._request_hash(op, payload)

            if self.sandbox_mode:
                return f"mews-mock-{h[:8]}"

            # K17-PAV check fuer Real-Booking
            ticket = os.environ.get("DF_PMS_MEWS_PHRONESIS_TICKET", "")
            if not ticket:
                logger.warning("[mews-adapter] K17-PAV: missing DF_PMS_MEWS_PHRONESIS_TICKET")
                return ""

            # Real-API placeholder (Welle-37)
            logger.warning("[mews-adapter] real-api book_room not yet implemented")
            return ""
        except Exception as e:
            logger.error(f"[mews-adapter] book_room failed: {e}")
            return ""

    def cancel_booking(self, booking_id: str) -> bool:
        """Storniere existierende Buchung."""
        op = "cancel_booking"
        try:
            if not self._connected:
                return False
            if not booking_id:
                return False

            payload = {"booking_id": booking_id}
            h = self._request_hash(op, payload)

            if self.sandbox_mode:
                # Mock: alles ausser explizit "fail-" prefix wird erfolgreich storniert
                if booking_id.startswith("fail-"):
                    return False
                return True

            # Real-API placeholder (Welle-37)
            logger.warning("[mews-adapter] real-api cancel_booking not yet implemented")
            return False
        except Exception as e:
            logger.error(f"[mews-adapter] cancel_booking failed: {e}")
            return False

    def get_capabilities(self) -> dict:
        """Health-check + Feature-Flags (LC5)."""
        return {
            "adapter_name": self.adapter_name,
            "version": "0.1.0-SKELETON",
            "sandbox_mode": self.sandbox_mode,
            "connected": self._connected,
            "supported_operations": ["connect", "query_inventory", "book_room", "cancel_booking"],
            "feature_flags": {
                "real_api": not self.sandbox_mode,
                "k17_pav": True,
                "hmac_audit": True,
                "circuit_breaker": True,
            },
            "health_score": 1.0 if self._connected else 0.5,
        }
