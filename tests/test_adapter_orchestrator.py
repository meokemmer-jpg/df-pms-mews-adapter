"""Tests fuer MEWSAdapterOrchestrator [CRUX-MK].

Welle-36 LaunchAgent-Entry-Point Tests.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.adapter_orchestrator import MEWSAdapterOrchestrator, LoopReport


class TestOrchestratorSandbox:
    """Sandbox-Mode Standard-Run."""

    def test_orchestrator_init_default_sandbox(self, monkeypatch):
        monkeypatch.delenv("DF_PMS_MEWS_REAL_ENABLED", raising=False)
        orch = MEWSAdapterOrchestrator()
        assert orch.sandbox_mode is True
        assert orch.tenant_id == "hildesheim"

    def test_orchestrator_init_custom_tenant(self):
        orch = MEWSAdapterOrchestrator(tenant_id="munich")
        assert orch.tenant_id == "munich"

    def test_orchestrator_run_sandbox_complete(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        orch = MEWSAdapterOrchestrator()
        report = orch.run("hildesheim")
        assert isinstance(report, LoopReport)
        assert report.df_id == "df-pms-mews-adapter"
        assert report.sandbox_mode is True
        assert report.final_status in ("complete", "partial")
        assert "auth" in report.phases_passed
        assert "connect" in report.phases_passed
        assert "health_check" in report.phases_passed

    def test_orchestrator_dry_run_skips_sample_query(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        orch = MEWSAdapterOrchestrator()
        report = orch.run("hildesheim", dry_run=True)
        assert "sample_query" not in report.phases_passed
        assert report.final_status in ("complete", "partial")

    def test_orchestrator_loop_report_persisted(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        orch = MEWSAdapterOrchestrator()
        report = orch.run("hildesheim")
        reports_dir = tmp_path / "runs" / "loop-reports"
        assert reports_dir.exists()
        files = list(reports_dir.glob("loop-*.json"))
        assert len(files) >= 1
