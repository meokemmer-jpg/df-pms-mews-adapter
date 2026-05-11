"""df-pms-mews-adapter [CRUX-MK].

Welle-36 HeyLou-Mosaic-Adapter fuer MEWS PMS (Industry-Leader).

LAZY-IMPORT-PATTERN: Module werden bei Bedarf importiert, kein Eager-Import
in __init__ um Circular-Imports + Startup-Latenz zu vermeiden.
"""

from __future__ import annotations

__version__ = "0.1.0-SKELETON"
__df_id__ = "df-pms-mews-adapter"
__welle__ = "welle-36"


def get_connector():
    """Lazy-Import MEWSConnector."""
    from src.mews_adapter import MEWSConnector
    return MEWSConnector


def get_oauth_manager():
    """Lazy-Import MEWSOAuthManager."""
    from src.mews_oauth import MEWSOAuthManager
    return MEWSOAuthManager


def get_orchestrator():
    """Lazy-Import MEWSAdapterOrchestrator."""
    from src.adapter_orchestrator import MEWSAdapterOrchestrator
    return MEWSAdapterOrchestrator


def get_audit_logger():
    """Lazy-Import AuditLogger."""
    from src.audit_logger import AuditLogger
    return AuditLogger


__all__ = [
    "__version__",
    "__df_id__",
    "__welle__",
    "get_connector",
    "get_oauth_manager",
    "get_orchestrator",
    "get_audit_logger",
]
