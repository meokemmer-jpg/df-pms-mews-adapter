
# K12+K13+K16 Trinity-CONTRARIAN 2026-05-17 (Cross-LLM-validated)
def k12_provenance(payload: bytes, key: bytes = b"df-trinity-contrarian-v1") -> dict:
    import hashlib, hmac
    return {
        "payload_hash": hashlib.sha256(payload).hexdigest(),
        "hmac_sha256": hmac.new(key, payload, hashlib.sha256).hexdigest(),
    }

def k13_anchor(payload_hash: str) -> dict:
    from datetime import datetime, timezone
    return {
        "anchor_type": "rfc3161-mock",
        "iso_ts": datetime.now(timezone.utc).isoformat(),
        "payload_hash": payload_hash,
    }

def k16_lock_or_exit(df_name: str):
    import fcntl, os, sys
    lock_path = f"/tmp/df-trinity-{df_name}.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        sys.exit(3)

"""Tests fuer MEWSOAuthManager [CRUX-MK].

Welle-36 ENV-Var-gated Sandbox-Pflicht-Tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.mews_oauth import MEWSOAuthManager, MEWSCredentials


class TestMEWSOAuthSandbox:
    """Sandbox-Default-Mode."""

    def test_oauth_sandbox_returns_mock_credentials(self):
        oauth = MEWSOAuthManager(sandbox_mode=True)
        creds = oauth.get_credentials("hildesheim")
        assert creds is not None
        assert creds.client_token == MEWSOAuthManager.MOCK_CLIENT_TOKEN
        assert creds.access_token == MEWSOAuthManager.MOCK_ACCESS_TOKEN
        assert creds.source == "mock"

    def test_oauth_validate_mock_credentials(self):
        oauth = MEWSOAuthManager(sandbox_mode=True)
        creds = oauth.get_credentials("hildesheim")
        assert oauth.validate(creds) is True

    def test_oauth_validate_none_returns_false(self):
        oauth = MEWSOAuthManager(sandbox_mode=True)
        assert oauth.validate(None) is False

    def test_oauth_default_is_sandbox(self, monkeypatch):
        monkeypatch.delenv("DF_PMS_MEWS_REAL_ENABLED", raising=False)
        oauth = MEWSOAuthManager()
        assert oauth.sandbox_mode is True


class TestMEWSOAuthRealMode:
    """Real-Mode mit ENV-Vars."""

    def test_oauth_real_mode_without_env_vars_returns_none(self, monkeypatch):
        monkeypatch.setenv("DF_PMS_MEWS_REAL_ENABLED", "true")
        monkeypatch.delenv("MEWS_CLIENT_TOKEN", raising=False)
        monkeypatch.delenv("MEWS_ACCESS_TOKEN", raising=False)
        oauth = MEWSOAuthManager()
        creds = oauth.get_credentials("hildesheim")
        assert creds is None

    def test_oauth_real_mode_with_env_vars_returns_creds(self, monkeypatch):
        monkeypatch.setenv("DF_PMS_MEWS_REAL_ENABLED", "true")
        monkeypatch.setenv("MEWS_CLIENT_TOKEN", "test-client-token")
        monkeypatch.setenv("MEWS_ACCESS_TOKEN", "test-access-token")
        oauth = MEWSOAuthManager()
        creds = oauth.get_credentials("hildesheim")
        assert creds is not None
        assert creds.client_token == "test-client-token"
        assert creds.access_token == "test-access-token"
        assert creds.source == "env"

    def test_oauth_is_real_mode_flag(self, monkeypatch):
        monkeypatch.setenv("DF_PMS_MEWS_REAL_ENABLED", "true")
        oauth = MEWSOAuthManager()
        assert oauth.is_real_mode() is True
