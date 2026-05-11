"""MEWS-OAuth-Manager [CRUX-MK].

MEWS verwendet ein Dual-Token-Pattern:
- ClientToken: identifiziert die Integration (per Integration registriert)
- AccessToken: identifiziert das Property/den Mandanten (per Property)

Beide tokens werden im POST-Body gesendet (nicht in Header) — MEWS-API-Standard.

ENV-Var-gated: ohne MEWS_CLIENT_TOKEN+MEWS_ACCESS_TOKEN -> Mock-Mode.

Welle-36.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MEWSCredentials:
    """Kanonische MEWS-Credentials.

    source ∈ {"env", "mock", "vault"}
    """
    client_token: str
    access_token: str
    source: str
    fetched_iso: str


class MEWSOAuthManager:
    """Manager fuer MEWS Dual-Token-Auth.

    Public API:
    - get_credentials(tenant_id) -> MEWSCredentials | None
    - validate(creds) -> bool
    - refresh_if_expired(creds) -> MEWSCredentials | None

    Sandbox-Default: liefert Mock-Credentials.
    """

    MOCK_CLIENT_TOKEN = "mock-client-token-hildesheim-2026"
    MOCK_ACCESS_TOKEN = "mock-access-token-property-001"

    def __init__(self, sandbox_mode: Optional[bool] = None):
        if sandbox_mode is None:
            self.sandbox_mode = os.environ.get("DF_PMS_MEWS_REAL_ENABLED", "false") != "true"
        else:
            self.sandbox_mode = sandbox_mode

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_credentials(self, tenant_id: str = "hildesheim") -> Optional[MEWSCredentials]:
        """Holt Credentials aus ENV oder liefert Mock im Sandbox-Mode.

        Returns None wenn Real-Mode aber ENV-Vars fehlen.
        """
        if self.sandbox_mode:
            return MEWSCredentials(
                client_token=self.MOCK_CLIENT_TOKEN,
                access_token=self.MOCK_ACCESS_TOKEN,
                source="mock",
                fetched_iso=self._now_iso(),
            )

        client_token = os.environ.get("MEWS_CLIENT_TOKEN", "")
        access_token = os.environ.get("MEWS_ACCESS_TOKEN", "")

        if not client_token or not access_token:
            logger.warning(
                f"[mews-oauth] missing credentials for tenant={tenant_id} "
                f"(MEWS_CLIENT_TOKEN={'set' if client_token else 'EMPTY'}, "
                f"MEWS_ACCESS_TOKEN={'set' if access_token else 'EMPTY'})"
            )
            return None

        return MEWSCredentials(
            client_token=client_token,
            access_token=access_token,
            source="env",
            fetched_iso=self._now_iso(),
        )

    def validate(self, creds: Optional[MEWSCredentials]) -> bool:
        """Strukturelle Validierung der Credentials (kein Live-API-Call).

        Live-API-Validation passiert beim connect().
        """
        if creds is None:
            return False
        if not creds.client_token or not creds.access_token:
            return False
        if creds.source not in ("env", "mock", "vault"):
            return False
        return True

    def refresh_if_expired(self, creds: Optional[MEWSCredentials]) -> Optional[MEWSCredentials]:
        """MEWS-Tokens sind grundsaetzlich lang-lebig (nicht JWT mit exp).

        Re-Fetch nur wenn Credentials lokal nicht mehr validierbar oder fetched_iso
        aelter als 24h (Sicherheits-Refresh fuer Re-Validation).
        """
        if not self.validate(creds):
            return self.get_credentials()

        # Re-Fetch nach 24h als Sicherheits-Mass
        try:
            fetched = datetime.fromisoformat(creds.fetched_iso)
            now = datetime.now(timezone.utc)
            if now - fetched > timedelta(hours=24):
                logger.info(f"[mews-oauth] credentials older than 24h, re-fetching")
                return self.get_credentials()
        except (ValueError, TypeError) as e:
            logger.warning(f"[mews-oauth] fetched_iso parse failed: {e}, re-fetching")
            return self.get_credentials()

        return creds

    def is_real_mode(self) -> bool:
        return not self.sandbox_mode
