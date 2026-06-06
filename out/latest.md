# df-pms-mews-adapter — Output [CRUX-MK]
*Autonom aktiviert 2026-06-05T15:52:05.541460+00:00 | ollama-local/qwen2.5:14b-instruct*

# Dokumentation für DF-PMS-Mews-Adapter

## Allgemeine Informationen

### Identität
- **Name:** MEWS PMS Adapter
- **Root Pfad:** /Users/make/Projects/dark-factories/df-pms-mews-adapter
- **Generiert am:** 2026-05-12T19:29:56+00:00

### Zweck und Umfang
Dieser Dark Factory dokumentiert den Codezustand über AST-Evidenz, wie Modu
Module, API-Kontrakte, Dataclass-Felder, ENV-Vars und Docstrings.

## Architekturkomponenten

- **MEWSConnector:** Verwaltet Booking/Reservation/Inventory-APIs.
- **MEWSOAuthManager:** Handhabt Client-Token + Access-Token-Pattern (ENV-V
(ENV-Var-gated).
- **MEWSAdapterOrchestrator:** LaunchAgent-Eingangs-Punkt für den Adapter.
- **AuditLogger:** HMAC-SHA256 JSONL append-only für Audit-Spur.

## Umgebungsvariablen

| Var | Standardwert | Pflichtige Einstellung | Beschreibung |
| --- | ------------ | ---------------------- | ------------- |
| `DF_PMS_MEWS_REAL_ENABLED` | false | nein | Aktiviert Real-API. Default i
ist Mock-Modus. |
| `MEWS_CLIENT_TOKEN` | "" | bei Real | Client-Token für Vendor-API (nur be
bei Real-Integration). |
| `MEWS_ACCESS_TOKEN` | "" | bei Real | Access-Token für Vendor-API (nur be
bei Real-Integration). |
| `DF_PMS_MEWS_PHRONESIS_TICKET` | "" | bei Real-Booking | K17-PAV Pflicht-
Pflicht-Ticket. |
| `DF_PMS_MEWS_HMAC_SECRET` | "" | nein | Geheimer Schlüssel für Audit-Sign
Audit-Signatur (optional). |
| `DF_PMS_MEWS_TENANT_ID` | hildesheim | nein | Identifikator des Mandanten
Mandanten (Default ist 'hildesheim'). |

## Sandbox-Modus

Liefert deterministische Mock-Daten:

- 3 Mock-Hotels: Hildesheim, Cape Coral, München.
- Jedes Hotel hat 5 Mock-Buchungen.
- Mock-Rates basierend auf einem Nachfrage-Index.

## Installation und Tests
Führen Sie die folgenden Schritte aus, um den Adapter zu installieren:

```bash
cp scripts/com.kemmer.df-pms-mews-adapter.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.kemmer.df-pms-mews-adapter.plist
```

Tests können durchgeführt werden mit:

```bash
python3 -m pytest tests/ -v
```

## Referenzen

- `~/.claude/rules/df-akzeptanz-kriterien.md` (K11-K16)
- `~/.claude/rules/df-lose-coupling.md` (LC1-LC5)
- `~/.claude/rules/env-var-gated-real-integration-default.md` (Sandbox-Defa
(Sandbox-Default)

## Status Welle 36
- **Tier:** SKELETON-CONDITIONAL
- **Promotion-Pfad:** PRE-PRODUCTION-CONDITIONAL nach Cross-LLM-Audit und R
Real-API-Pilot für 30 Tage in Hildesheim.
- **LaunchAgent-Cadence:** 7200s (2 Stunden).

Diese Dokumentation dient zur Verwendung im Kontext von HeyLou Travel, spez
spezifisch für den MEWS PMS Adapter. Die Struktur und Details sind eng mit 
den Kriterien der CRUX-MK-Konformität verflochten, um Sicherheit, Transpare
Transparenz und Qualität zu gewährleisten.

(rho-rückgebunden: ca. 25k EUR/Jahr)