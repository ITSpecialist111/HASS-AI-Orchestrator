# AI Visual Dashboard

This is the visualization engine for the **AI Orchestrator**, responsible for generating dynamic, visually rich Home Assistant dashboards using LLMs. While integrated into the main orchestrator, it can also be tested as a standalone module.

## Features
- **Dynamic Visualization**: Uses LLMs (Local or Cloud) to transform raw HA entity data into a beautiful HTML/Tailwind dashboard.
- **Auto-Refresh**: Automatically updates the dashboard periodically.
- **Mixergy Style**: Prompts the AI for a high-fidelity, skeuomorphic "Mixergy-style" design.
- **Mock Mode**: Works out of the box with sample data for demonstration.

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your details:
   - `HA_URL`: Your Home Assistant instance URL.
   - `HA_ACCESS_TOKEN`: A Long-Lived Access Token.
   - `GEMINI_API_KEY`: Your Google Cloud AI API Key (Required for high-fidelity mode).

## Running
```bash
python dashboard_gen.py
```
This will generate an `index.html` file in the current directory and refresh it periodically.
