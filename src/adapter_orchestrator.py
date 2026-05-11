"""MEWS-Adapter-Orchestrator [CRUX-MK].

LaunchAgent-Entry-Point fuer Welle-36 HeyLou-Mosaic-Adapter MEWS.

Orchestriert:
1. OAuth-Auth via MEWSOAuthManager
2. Connect via MEWSConnector
3. Health-Check via get_capabilities()
4. Optional: Sample-Query auf Sandbox-Hotels
5. Audit-Log via AuditLogger

LC1 graceful_degradation: bei Failures wechselt Mode auf 'standalone_mock'.
LC5 health_check: persistiert State in audit/.

Welle-36.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class LoopReport:
    """Report-Format fuer LaunchAgent-Loop."""
    loop_id: str
    df_id: str
    started_iso: str
    finished_iso: str
    sandbox_mode: bool
    final_status: str            # "complete" | "partial" | "failed"
    phases_passed: list = field(default_factory=list)
    phases_failed: list = field(default_factory=list)
    artifacts: dict = field(default_factory=dict)
    error: Optional[str] = None


class MEWSAdapterOrchestrator:
    """Orchestriert MEWS-Adapter-LaunchAgent-Run.

    Standalone-Mode: keine Cross-DF-Dependencies.
    """

    DF_ID = "df-pms-mews-adapter"

    def __init__(self, tenant_id: Optional[str] = None):
        self.tenant_id = tenant_id or os.environ.get("DF_PMS_MEWS_TENANT_ID", "hildesheim")
        self.sandbox_mode = os.environ.get("DF_PMS_MEWS_REAL_ENABLED", "false") != "true"

        # Lazy imports
        from src.mews_oauth import MEWSOAuthManager
        from src.mews_adapter import MEWSConnector
        from src.audit_logger import AuditLogger

        self.oauth = MEWSOAuthManager(sandbox_mode=self.sandbox_mode)
        self.connector = MEWSConnector(sandbox_mode=self.sandbox_mode)
        self.audit = AuditLogger(df_id=self.DF_ID)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _persist_loop_report(self, report: LoopReport) -> Optional[Path]:
        """Persistiert LoopReport als JSON in runs/loop-reports/."""
        try:
            reports_dir = Path("runs/loop-reports")
            reports_dir.mkdir(parents=True, exist_ok=True)
            file_path = reports_dir / f"loop-{report.loop_id}.json"
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(asdict(report), f, indent=2, default=str)
            return file_path
        except Exception as e:
            logger.error(f"loop-report persist failed: {e}")
            return None

    def run(self, hotel_id: Optional[str] = None, dry_run: bool = False) -> LoopReport:
        """Execute LaunchAgent-Loop.

        Phases:
        1. auth -> credentials geholt
        2. connect -> connector verbunden
        3. health_check -> capabilities geholt
        4. sample_query -> inventur-query (Sandbox-Hotel)
        5. audit_persist -> alle Phasen audited

        Returns LoopReport mit final_status.
        """
        loop_id = str(uuid.uuid4())[:8]
        started = self._now_iso()
        report = LoopReport(
            loop_id=loop_id,
            df_id=self.DF_ID,
            started_iso=started,
            finished_iso="",
            sandbox_mode=self.sandbox_mode,
            final_status="failed",
        )

        hotel_id = hotel_id or self.tenant_id

        try:
            # Phase 1: Auth
            try:
                creds = self.oauth.get_credentials(self.tenant_id)
                if not self.oauth.validate(creds):
                    report.phases_failed.append("auth")
                    report.error = "auth: invalid credentials"
                    self.audit.log("auth_failed", {"tenant_id": self.tenant_id, "loop_id": loop_id}, target="mews-auth")
                else:
                    report.phases_passed.append("auth")
                    self.audit.log("auth_ok", {"tenant_id": self.tenant_id, "source": creds.source, "loop_id": loop_id}, target="mews-auth")
            except Exception as e:
                report.phases_failed.append("auth")
                report.error = f"auth: {e}"
                logger.error(f"[orchestrator] auth phase failed: {e}")

            if "auth" in report.phases_failed and not self.sandbox_mode:
                # Hard-Stop bei Real-Mode + Auth-Failure
                report.finished_iso = self._now_iso()
                report.final_status = "failed"
                self._persist_loop_report(report)
                return report

            # Phase 2: Connect
            try:
                creds_dict = {
                    "client_token": creds.client_token if creds else "",
                    "access_token": creds.access_token if creds else "",
                }
                connected = self.connector.connect(creds_dict)
                if connected:
                    report.phases_passed.append("connect")
                    self.audit.log("connect_ok", {"tenant_id": self.tenant_id, "loop_id": loop_id}, target="mews-operations")
                else:
                    report.phases_failed.append("connect")
                    self.audit.log("connect_failed", {"tenant_id": self.tenant_id, "loop_id": loop_id}, target="mews-operations")
            except Exception as e:
                report.phases_failed.append("connect")
                logger.error(f"[orchestrator] connect phase failed: {e}")

            # Phase 3: Health-Check
            try:
                caps = self.connector.get_capabilities()
                report.artifacts["capabilities"] = caps
                report.phases_passed.append("health_check")
            except Exception as e:
                report.phases_failed.append("health_check")
                logger.error(f"[orchestrator] health_check failed: {e}")

            # Phase 4: Sample-Query (Sandbox only, dry_run skips)
            if not dry_run and self.connector._connected:
                try:
                    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    tomorrow_iso = f"{today}T14:00:00Z"
                    inventory = self.connector.query_inventory(
                        hotel_id, (tomorrow_iso, tomorrow_iso)
                    )
                    report.artifacts["sample_inventory_count"] = len(inventory)
                    report.phases_passed.append("sample_query")
                    self.audit.log("sample_query_ok", {"hotel_id": hotel_id, "rooms": len(inventory), "loop_id": loop_id}, target="mews-operations")
                except Exception as e:
                    report.phases_failed.append("sample_query")
                    logger.error(f"[orchestrator] sample_query failed: {e}")

            # Phase 5: Audit-Persist
            try:
                self.audit.log(
                    "loop_complete",
                    {
                        "loop_id": loop_id,
                        "phases_passed": report.phases_passed,
                        "phases_failed": report.phases_failed,
                        "sandbox_mode": self.sandbox_mode,
                    },
                    target="mews-operations",
                )
                report.phases_passed.append("audit_persist")
            except Exception as e:
                report.phases_failed.append("audit_persist")
                logger.error(f"[orchestrator] audit_persist failed: {e}")

            # Final-Status
            if not report.phases_failed:
                report.final_status = "complete"
            elif len(report.phases_passed) >= 3:
                report.final_status = "partial"
            else:
                report.final_status = "failed"

        except Exception as e:
            report.error = f"orchestrator: {e}"
            report.final_status = "failed"
            logger.error(f"[orchestrator] unhandled exception: {e}")
        finally:
            report.finished_iso = self._now_iso()
            self._persist_loop_report(report)

        return report


def main():
    """Entry-Point fuer LaunchAgent."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    orch = MEWSAdapterOrchestrator()
    report = orch.run()
    print(f"[df-pms-mews-adapter] loop_id={report.loop_id} status={report.final_status} sandbox={report.sandbox_mode}")
    sys.exit(0 if report.final_status in ("complete", "partial") else 1)


if __name__ == "__main__":
    main()
