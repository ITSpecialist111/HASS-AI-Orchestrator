# Changelog

## [0.9.22] - 2025-12-21
### Fixed
- **No Route to Host**: Enabled **Host Networking** for the addon. This allows the backend to reach Ollama and other local network devices (e.g. 192.168.x.x) directly.
- **Startup Crash**: Fixed a `NoneType` error where the Knowledge Base would try to sync before the Home Assistant connection was ready.
- **Telemetry Silence**: Moved telemetry suppression to the start of the application to ensure logs stay clean.
- **Connectivity Check**: Added a startup reachability test for the Ollama host with helpful error diagnostics.

## [0.9.21] - 2025-12-20
