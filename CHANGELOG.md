# Changelog

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
