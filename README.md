# df-pms-mews-adapter [CRUX-MK]

**12. Foundation-DF (Welle-36 HeyLou-Mosaic-Layer): MEWS PMS-Adapter (Industry-Leader).**

Mosaic-Adapter fuer MEWS Property Management System. ENV-Var-gated Sandbox-Default-Mode, Mock-Fallback Pflicht, K17-PAV Pre-Action-Verification, HMAC-SHA256 Audit-Trail.

## Architektur

- `MEWSConnector` (Booking/Reservation/Inventory-API)
- `MEWSOAuthManager` (Client-Token + Access-Token-Pattern, ENV-Var-gated)
- `MEWSAdapterOrchestrator` (LaunchAgent-Entry-Point)
- `AuditLogger` (HMAC-SHA256 JSONL append-only)

## CRUX-Konformitaet

- K11 Cascade-Containment: hard isolation, blast_radius=1
- K12 Distillation-Resistenz: provenance_required, non_llm_validation_layer
- K13 Pre-Action-Verification: env_tag + backup + blast_radius
- K14 Human-Override: single_command, weekly_review
- K15 Entropy-Budget: ~600 LOC, rho ~25k EUR/J
- K16 Concurrent-Spawn-Mutex: wrapper_mutex + engine_pgrep_check
- LC1-LC5 Lose-Coupling: 4 degradation-modes, direct_mode_capability=0.5

## ENV-Vars

| Var | Default | Pflicht | Beschreibung |
|-----|---------|---------|--------------|
| `DF_PMS_MEWS_REAL_ENABLED` | `false` | nein | Aktiviert Real-API. Sonst Mock. |
| `MEWS_CLIENT_TOKEN` | `""` | bei Real | Client-Token (Vendor-API) |
| `MEWS_ACCESS_TOKEN` | `""` | bei Real | Access-Token (Vendor-API) |
| `DF_PMS_MEWS_PHRONESIS_TICKET` | `""` | bei Real-Booking | K17-PAV Pflicht-Ticket |
| `DF_PMS_MEWS_HMAC_SECRET` | `""` | nein | Audit-Signature-Secret |
| `DF_PMS_MEWS_TENANT_ID` | `hildesheim` | nein | Mandant |

## Sandbox-Mode (Default)

Liefert deterministische Mock-Daten:
- 3 Mock-Hotels (Hildesheim, Cape Coral, Munich)
- 5 Mock-Bookings pro Hotel
- Mock-Rates per Demand-Index

## Welle-36 Status

- Tier: SKELETON-CONDITIONAL
- Promotion-Pfad: PRE-PRODUCTION-CONDITIONAL nach Cross-LLM-Audit + Real-API-Pilot 30 Tage Hildesheim
- LaunchAgent-Cadence: 7200s (2h)

## Install

```bash
cp scripts/com.kemmer.df-pms-mews-adapter.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.kemmer.df-pms-mews-adapter.plist
```

## Tests

```bash
python3 -m pytest tests/ -v
```

## Referenzen

- `~/.claude/rules/df-akzeptanz-kriterien.md` (K11-K16)
- `~/.claude/rules/df-lose-coupling.md` (LC1-LC5)
- `~/.claude/rules/env-var-gated-real-integration-default.md` (Sandbox-Default)
- `branch-hub/findings/HEYLOU-TRAVEL-MOSAIC-PLAN-WELLE-35-PLUS-2026-05-11.md`

[CRUX-MK]
