import asyncio
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from ha_client import HAWebSocketClient

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load Environment Variables
load_dotenv()

HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REFRESH_MINUTES = int(os.getenv("REFRESH_INTERVAL_MINUTES", 5))
TARGET_ENTITIES = os.getenv("TARGET_ENTITIES", "").split(",")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

SYSTEM_PROMPT = """
You are a World-Class Data Visualization Expert and UI Designer specializing in High-End Smart Home Dashboards.
Your goal is to create a "Mixergy Smart Dashboard" (Dashboard View) using a standalone HTML/Tailwind CSS file.

VISUAL & LAYOUT REQUIREMENTS (IT MUST 'POP'):
1. STYLE: "Deep Ocean" aesthetic. Dark blue/slate backgrounds (bg-slate-900), glassmorphism (backdrop-blur-md), and neon accents.
2. LAYOUT: A 3-column grid:
    - LEFT (Control): "Energy Logic" flow (inputs from Grid/Battery/Solar leading to a decision) and "Quick Actions" (Buttons like Shower/Bath).
    - CENTER (Hero): A "TankVisual" component. This is a vertical pill-shaped glass tank. 
      - Use a CSS gradient (blue to cyan) that fills up based on the 'charge' level %.
      - If 'is_charging' is true, add animated rising bubbles (CSS animations).
      - Add backdrop-blur to the tank glass and a ring-2 glow effect using Tailwind for active state.
    - RIGHT (Analytics): Cost cards (comparing Electric vs Gas rates) and Heat Loss charts/stats.
3. COMPONENTS:
    - Use Lucide Icons (via CDN) or SVG icons.
    - Ensure smooth CSS transitions when levels change.
    - Give cards a ring-2 glow effect and deep shadows.
4. DATA HANDLING: 
    - Include a mock `useHomeAssistant` persistent state object in a <script> tag.
    - Key States to handle: charge (%), temp (°C), is_charging (bool), grid_export (kW), and decision_reason (string).

OUTPUT REQUIREMENTS:
- Provide ONLY the complete, standalone HTML/CSS/JS code.
- No markdown wrappers, no explanations. Just the HTML.
"""

async def generate_dashboard(mock_mode=False):
    # 1. Connect to Home Assistant
    if mock_mode:
        logger.info("MOCK MODE: Using sample Mixergy data...")
        relevant_states = [
            {"entity_id": "sensor.tank_charge", "state": "75", "attributes": {"unit_of_measurement": "%", "friendly_name": "Tank Charge"}},
            {"entity_id": "sensor.tank_temp", "state": "52.4", "attributes": {"unit_of_measurement": "°C", "friendly_name": "Water Temp"}},
            {"entity_id": "binary_sensor.tank_is_heating", "state": "on", "attributes": {"friendly_name": "Heat Pump Active"}},
            {"entity_id": "sensor.grid_export", "state": "1.2", "attributes": {"unit_of_measurement": "kW", "friendly_name": "Grid Export"}},
            {"entity_id": "sensor.decision", "state": "Heating via Heat Pump", "attributes": {"reason": "Low electricity tariff + Solar surplus detected"}}
        ]
    else:
        client = HAWebSocketClient(HA_URL, HA_TOKEN)
        try:
            logger.info("Connecting to Home Assistant...")
            await client.connect()
            
            logger.info("Fetching states...")
            all_states = await client.get_states()
            
            # Filter for Mixergy-relevant states or similar
            # In a real scenario, TARGET_ENTITIES would be set
            relevant_states = []
            if TARGET_ENTITIES and TARGET_ENTITIES[0]:
                relevant_states = [s for s in all_states if s['entity_id'] in TARGET_ENTITIES]
            else:
                interesting_domains = ['sensor', 'climate', 'light', 'binary_sensor']
                relevant_states = [s for s in all_states if s['entity_id'].split('.')[0] in interesting_domains][:20]
        except Exception as e:
            logger.error(f"Error during state retrieval: {e}")
            return
        finally:
            await client.disconnect()

    logger.info(f"Collected {len(relevant_states)} entities for visualization.")
    
    # 3. Prepare Prompt
    data_json = json.dumps(relevant_states, indent=2)
    prompt = f"Generate the Mixergy Smart Dashboard for these entities:\n\n{data_json}"
    
    # 4. Call Gemini
    if mock_mode:
        logger.info("MOCK MODE: Generating Mixergy style HTML placeholder...")
        # Since I am an AI, I can generate the "Pop" version of the HTML here
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <title>Mixergy Smart Dashboard (MOCK)</title>
    <style>
        body {{ font-family: 'Outfit', sans-serif; background-color: #0f172a; color: #f8fafc; overflow-x: hidden; }}
        .glass {{ background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.1); }}
        .tank-glow {{ box-shadow: 0 0 30px rgba(56, 189, 248, 0.3); }}
        .glow-orange {{ box-shadow: 0 0 20px rgba(249, 115, 22, 0.2); }}
        
        .bubble {{
            position: absolute; bottom: 0; background: rgba(255, 255, 255, 0.4);
            border-radius: 50%; animation: rise 3s infinite ease-in;
        }}
        @keyframes rise {{
            0% {{ transform: translateY(0) scale(1); opacity: 0; }}
            50% {{ opacity: 0.6; }}
            100% {{ transform: translateY(-200px) scale(0.5); opacity: 0; }}
        }}
        .water-gradient {{ background: linear-gradient(to top, #0ea5e9, #22d3ee); }}
    </style>
</head>
<body class="p-6 md:p-12 min-h-screen">
    <div class="max-w-7xl mx-auto">
        <header class="flex justify-between items-center mb-12">
            <div>
                <h1 class="text-3xl font-extrabold tracking-tight">Mixergy <span class="font-light text-slate-500">Smart</span></h1>
                <p class="text-xs font-bold text-sky-500 uppercase tracking-[0.2em]">Energy Intelligence Active</p>
            </div>
            <div class="flex items-center gap-6">
                <div class="text-right">
                    <p class="text-[10px] font-bold text-slate-500 uppercase">Decision Engine</p>
                    <p class="text-sm font-semibold text-green-400">Low Electricity Tariff Detected</p>
                </div>
                <div class="w-12 h-12 glass rounded-2xl flex items-center justify-center ring-1 ring-white/10">
                    <div class="w-3 h-3 bg-green-500 rounded-full animate-pulse shadow-[0_0_10px_rgba(34,197,94,0.5)]"></div>
                </div>
            </div>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <!-- LEFT: Control -->
            <div class="space-y-6">
                <div class="glass p-8 rounded-[2.5rem] ring-1 ring-white/5">
                    <h2 class="text-lg font-bold mb-6 flex items-center gap-2">
                        <span class="w-2 h-6 bg-sky-500 rounded-full"></span> Energy Logic
                    </h2>
                    <div class="space-y-4">
                        <div class="flex justify-between items-center p-4 bg-white/5 rounded-2xl border border-white/5">
                            <span class="text-sm text-slate-400">Solar Yield</span>
                            <span class="font-bold text-amber-400">2.4 kW</span>
                        </div>
                        <div class="flex justify-between items-center p-4 bg-white/5 rounded-2xl border border-white/5">
                            <span class="text-sm text-slate-400">Battery State</span>
                            <span class="font-bold text-sky-400">88%</span>
                        </div>
                        <div class="flex justify-between items-center p-4 bg-sky-500/10 rounded-2xl border border-sky-500/20 ring-1 ring-sky-500/30">
                            <span class="text-sm text-sky-100 italic">Decision: Use Heat Pump</span>
                            <span class="font-bold text-sky-400">ACTIVE</span>
                        </div>
                    </div>
                </div>

                <div class="glass p-8 rounded-[2.5rem] ring-1 ring-white/5">
                    <h2 class="text-lg font-bold mb-6">Quick Boost</h2>
                    <div class="grid grid-cols-2 gap-4">
                        <button class="aspect-square glass rounded-3xl flex flex-col items-center justify-center gap-3 transition-all hover:bg-sky-500/20 active:scale-95 group">
                            <span class="text-2xl group-hover:scale-110 transition-transform">🚿</span>
                            <span class="text-xs font-bold uppercase tracking-widest text-slate-300">Shower</span>
                        </button>
                        <button class="aspect-square glass rounded-3xl flex flex-col items-center justify-center gap-3 transition-all hover:bg-sky-500/20 active:scale-95 group">
                            <span class="text-2xl group-hover:scale-110 transition-transform">🛁</span>
                            <span class="text-xs font-bold uppercase tracking-widest text-slate-300">Bath</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- CENTER: Tank Visual -->
            <div class="glass p-12 rounded-[3.5rem] flex flex-col items-center justify-center relative overflow-hidden ring-1 ring-white/10 tank-glow">
                <div class="absolute inset-0 bg-gradient-to-b from-sky-500/5 to-transparent pointer-events-none"></div>
                
                <h3 class="text-sm font-black text-slate-500 uppercase tracking-[0.3em] mb-8">Thermal Storage</h3>
                
                <!-- The Tank -->
                <div class="relative w-40 h-[28rem] rounded-full border-4 border-slate-700/50 bg-slate-800/30 overflow-hidden shadow-2xl backdrop-blur-sm ring-4 ring-white/5">
                    <!-- Water Level -->
                    <div class="absolute bottom-0 w-full water-gradient transition-all duration-1000 ease-out flex items-center justify-center" style="height: 75%">
                        <!-- Bubbles if heating -->
                        <div class="bubble" style="left: 20%; width: 8px; height: 8px; animation-delay: 0.2s;"></div>
                        <div class="bubble" style="left: 50%; width: 12px; height: 12px; animation-delay: 0.8s;"></div>
                        <div class="bubble" style="left: 70%; width: 6px; height: 6px; animation-delay: 1.5s;"></div>
                        <div class="bubble" style="left: 30%; width: 10px; height: 10px; animation-delay: 2.1s;"></div>
                        <div class="bubble" style="left: 60%; width: 4px; height: 4px; animation-delay: 0.5s;"></div>
                        
                        <div class="text-center">
                            <p class="text-4xl font-extrabold text-white drop-shadow-md">75%</p>
                        </div>
                    </div>
                </div>

                <div class="mt-8 text-center">
                    <p class="text-5xl font-black text-white">52.4<span class="text-2xl text-slate-500 font-light ml-1">°C</span></p>
                    <p class="text-xs font-bold text-sky-400 mt-2 uppercase tracking-widest">Optimal Heat Level</p>
                </div>
            </div>

            <!-- RIGHT: Analytics -->
            <div class="space-y-6">
                <div class="glass p-8 rounded-[2.5rem] ring-1 ring-white/5">
                    <h2 class="text-lg font-bold mb-6">Cost Intelligence</h2>
                    <div class="space-y-6">
                        <div class="p-5 bg-white/5 rounded-3xl border border-white/5">
                            <p class="text-[10px] font-bold text-slate-500 uppercase mb-3">Rate Breakdown</p>
                            <div class="flex justify-between items-center">
                                <span class="text-sm font-semibold">Electric Tariff</span>
                                <span class="text-lg font-black text-sky-400">£0.07<span class="text-[10px] ml-1">/kWh</span></span>
                            </div>
                            <div class="mt-4 pt-4 border-t border-white/5 flex justify-between items-center">
                                <span class="text-sm font-semibold">Equivalent Gas</span>
                                <span class="text-lg font-black text-orange-400">£0.09<span class="text-[10px] ml-1">/kWh</span></span>
                            </div>
                        </div>
                        <div class="bg-green-500/10 p-4 rounded-2xl border border-green-500/20 text-center">
                            <p class="text-xs font-bold text-green-400 uppercase tracking-widest">Saving: £12.40 this week</p>
                        </div>
                    </div>
                </div>

                <div class="glass p-8 rounded-[2.5rem] ring-1 ring-white/5">
                    <h2 class="text-lg font-bold mb-6">Heat Retention</h2>
                    <div class="flex items-center justify-between gap-4">
                        <div class="flex-1 space-y-2">
                             <div class="h-1 bg-slate-700 rounded-full w-full">
                                <div class="h-full bg-sky-500 rounded-full w-[92%]"></div>
                             </div>
                             <div class="h-1 bg-slate-700 rounded-full w-full">
                                <div class="h-full bg-slate-600 rounded-full w-[85%]"></div>
                             </div>
                             <div class="h-1 bg-slate-700 rounded-full w-full">
                                <div class="h-full bg-slate-600 rounded-full w-[78%]"></div>
                             </div>
                        </div>
                        <div class="text-right">
                            <span class="text-3xl font-black text-white">0.4</span>
                            <span class="text-xs font-bold text-slate-500 block">kWh/Day loss</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <footer class="mt-12 text-center">
            <p class="text-[10px] font-bold text-slate-600 uppercase tracking-[.4em]">Integrated Intelligence • 2025 Ref v1.2</p>
        </footer>
    </div>
</body>
</html>
        """
    else:
        logger.info("Generating Mixergy dashboard with Gemini...")
        response = model.generate_content([SYSTEM_PROMPT, prompt])
        html_content = response.text
        if "```html" in html_content:
            html_content = html_content.split("```html")[1].split("```")[0]
        elif "```" in html_content:
            html_content = html_content.split("```")[1].split("```")[0]

    # 5. Save to local file
    output_path = "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content.strip())
        
    logger.info(f"Dashboard successfully generated and saved to {output_path}")

async def main_loop():
    logger.info("=== AI Visual Dashboard Started ===")
    mock_mode = not (HA_URL and HA_TOKEN and GEMINI_API_KEY)
    if mock_mode:
        logger.warning("Configuration missing. Running in MOCK MODE for visualization demo.")

    while True:
        await generate_dashboard(mock_mode=mock_mode)
        logger.info(f"Waiting {REFRESH_MINUTES} minutes for next refresh...")
        await asyncio.sleep(REFRESH_MINUTES * 60)

if __name__ == "__main__":
    if not HA_URL or not HA_TOKEN or not GEMINI_API_KEY:
        logger.error("Missing configuration in .env. Please check HA_URL, HA_ACCESS_TOKEN, and GEMINI_API_KEY.")
    else:
        asyncio.run(main_loop())
