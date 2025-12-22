# Changelog
<br>

## [0.9.45] - 2025-12-22
### Fixed
- **HA Connectivity Robustness**: Improved error logging in `ha_client.py` with full URI and exception details. Added a startup wait period in `main.py` to prevent race conditions during early ingestion.
- **Custom HA URL Support**: Modified `run.sh` to allow user-defined `HA_URL` (from `options.json`) to take precedence even when a Long-Lived Access Token is provided.
- **Improved Reliability**: Architect suggestions and Knowledge Base ingestion now handle connection delays more gracefully.
<br>
<br>

## [0.9.44] - 2025-12-22
### Fixed
- **Chat Tool Execution**: Resolved `UnboundLocalError` (cannot access local variable 'params') when the AI Assistant triggers tools.
- **Agent Persistence**: Standardized `agents.yaml` pathing to ensure agents created through the UI are saved to the persistent `/config/agents.yaml` in Home Assistant Add-on environments.
<br>
<br>

## [0.9.43] - 2025-12-22
### Added
- **Gemini LLM Integration**: Added world-class LLM support for visual dashboard generation using Google Gemini.
- **Model Choice**: Users can now choose between local Ollama and Gemini (highly recommended for high-fidelity designs).
- **Robotics Preview Model**: Specifically added support for `gemini-robotics-er-1.5-preview` for advanced spatial and thermal visualizations.
- **Integration Settings**: New configuration fields in the UI for Gemini API Key, Model Selection, and a prioritization toggle.
- **Runtime Updates**: Gemini settings can be updated in-memory from the UI without requiring a full server restart.
<br>

## [0.9.42] - 2025-12-22
### Added
- **AI Visual Dashboard (Dynamic)**: Fully integrated natural language dashboard generation. Users can now command the dashboard style and focus via chat or a new dedicated UI tab.
- **Dynamic AI Prompting**: The Orchestrator now uses specific user instructions (e.g., "cyberpunk style", "security-focused") to architect the dashboard's HTML/CSS.
- **Background Refresh**: Implemented a periodic background loop that refreshes dashboard data every 5 minutes while preserving the user's requested aesthetic.
- **Direct UI Integration**: Dashboard is now a first-class citizen of the main UI, rendered via iframe with dedicated refresh controls.
### Fixed
- **Windows Pathing**: Resolved path normalization issues for `dynamic.html` on Windows, ensuring reliable dashboard file retrieval outside the Add-on environment.
- **Connectivity Guards**: Added safeguards to ensure Home Assistant is connected before attempting dashboard generation, preventing empty "no results" views.

## [0.9.41] - 2025-12-21
### Fixed
- **Docker Image Integrity**: Updated `Dockerfile` to correctly include `agents.yaml`, `skills/`, and `translations/` in the build, resolving issues with missing agents and tools in the Add-on environment.

## [0.9.40] - 2025-12-21
### Fixed
- **Connectivity Fallback**: Implemented automatic fallback to Direct Core Access (`http://homeassistant:8123`) when the Home Assistant Supervisor Token is missing in Add-on mode.
- **Agent Configuration Path**: Updated `agents.yaml` loading to prioritize `/config/agents.yaml` for persistent storage in Home Assistant Add-ons.

## [0.9.39] - 2025-12-21
### Fixed
- **Deployment**: Version bump to force update detection in Home Assistant (functional equivalent to v0.9.38).

## [0.9.38] - 2025-12-21
### Fixed
- **Instantiation Fix**: Corrected keyword arguments for global `HAWebSocketClient` instantiation in `main.py` (`url` -> `ha_url`).

## [0.9.37] - 2025-12-21
### Fixed
- **Connectivity Restoration**: Restored missing `ha_client` instantiation in `main.py` which was causing global `NoneType` errors.
- **Architect Stability**: Added runtime guards to `ArchitectAgent` to prevent crashes when Home Assistant is unreachable.

## [0.9.36] - 2025-12-21
### Fixed
- **Agent Initialization**: Fixed `AttributeError` in `BaseAgent` and `ArchitectAgent` by correctly positioning property definitions, ensuring `decision_dir` and `logger` are properly initialized.

## [0.9.35] - 2025-12-21
### Fixed
- **Orchestrator Init**: Fixed `AttributeError` by correctly positioning the `ha_client` property definition outside the `__init__` method, ensuring full initialization of all attributes.

## [0.9.34] - 2025-12-21
### Fixed
- **Startup Logic**: Fixed `Orchestrator` initialization scope issues and added robust `None` checks in `KnowledgeBase` to handle lazy connection availability.

## [0.9.33] - 2025-12-21
### Fixed
- **Deployment Verification**: Added `VERSION` tag to `MCPServer` and removed ambiguous docstring to verify fresh code deployment.

## [0.9.32] - 2025-12-21
### Fixed
- **Integrity Fix**: Restored `mcp_server.py` to a clean state to eliminate persistent syntax errors.

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
