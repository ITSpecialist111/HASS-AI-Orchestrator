# Changelog

## [0.9.21] - 2025-12-20
### Fixed
- **Stability Restoration**: Reverted to v0.9.15 base and selectively applied critical stability fixes.
- **System Startup Hang**: Home Assistant connection is now backgrounded.
- **Telemetry Suppression**: Disabled broken ChromaDB telemetry.
- **WebSocket Resilience**: Increased keepalive timeouts to 60s.
- **Path Hardening**: Fixed double-slash routing issues in Ingress middleware.
