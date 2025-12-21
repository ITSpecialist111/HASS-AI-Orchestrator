# Changelog

## [0.9.31] - 2025-12-21
### Fixed
- **Hotfix**: Resolved SyntaxError in `MCPServer` caused by artifacts in v0.9.30 release.

## [0.9.30] - 2025-12-21
### Fixed
- **Startup Crash Loop**: Refactored entire backend to use Lazy Injection for `ha_client`. Use `lambda: ha_client` to resolve the connection object at runtime, preventing components from holding a stale `None` reference.

## [0.9.29] - 2025-12-21
### Fixed
- **Knowledge Base Crash**: Guarded `ingest_ha_registry` against `NoneType` WebSocket error during startup loop.
- **Connection Logic**: Clarified need for `ha_access_token` when Supervisor API injection fails.

## [0.9.28] - 2025-12-21
### Fixed
- **Critical Crash Fix**: Resolved `NoneType` error in Universal Agent when Entity Discovery runs without a connection.
- **Port Consistency**: Verified and locked internal port to 8999 to resolve potential Ingress mismatches.

## [0.9.27] - 2025-12-21
### Fixed
- **Emergency Fix**: Guarded `ha_client` against `NoneType` crashes when disconnected.
- **Dashboard**: Relaxed Ingress path normalization to fix "black screen" 404 errors.
- **Diagnostics**: Added cleaner error handling for failed WebSocket message artifacts.

## [0.9.26] - 2025-12-21
### Added
- Specific static mount for `/assets` to ensure Ingress consistency.
- Environment diagnostics for Home Assistant connection tokens.
### Fixed
- Improved Supervisor detection in Add-on environment (checks for `/data/options.json`).
- Read `ha_access_token` from add-on options if environment variables are missing.
- Refined Ingress middleware to prevent double-slash asset 404s.

## [v0.9.25] - 2025-12-21
- **Stability Fix**: Hardened Home Assistant WebSocket client against `NoneType` crashes.
- **Connection Logic**: Improved Supervisor URL detection in Add-on environment.
- **Resilience**: Added connection guards to Knowledge Base ingestion and Universal Agents to prevent startup race conditions.

## [v0.9.24] - 2025-12-21
- **Ingress Fix**: Added `IngressMiddleware` path normalization to fix "Black Screen" asset issues.
- **Trailing Slashes**: Enforced trailing slashes for dashboard root to ensure relative asset loading.

## [v0.9.23] - 2025-12-21
- **Telemetry Silence**: Monkey-patched PostHog in memory to stop log spam from ChromaDB.
- **Diagnostics**: Added deep network diagnostics (DNS, Socket, HTTP) to verify Ollama connectivity.
 black-screen issues in Ingress.
- **Ingress Performance**: Smoothed out double-slash normalization for all backend routes.

## [0.9.22] - 2025-12-21

## [0.9.21] - 2025-12-20
