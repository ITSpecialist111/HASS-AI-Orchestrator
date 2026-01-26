# Generate AI Visual Dashboard

## Purpose
Generates a custom AI-powered visual dashboard for Home Assistant using natural language description and entity context.

## Usage
`/generate-dashboard [description]`

Example: `/generate-dashboard "Create a dark theme energy dashboard with solar production, battery status, and grid usage in 3 columns"`

## Instructions for Agent

When this command is invoked:

1. **Parse User Request**:
   - Extract desired theme/style
   - Identify entity categories needed
   - Determine layout preferences
   - Note any specific requirements

2. **Gather Entity Context**:
   - Query Home Assistant for available entities
   - Filter entities by relevant domains
   - Get current states and attributes
   - Identify related entity groups

3. **Select LLM Provider**:
   - Use Gemini for high-fidelity/complex dashboards
   - Use Ollama for quick/simple dashboards
   - Consider token limits and generation time

4. **Prepare Generation Context**:
   ```json
   {
     "user_request": "[description]",
     "available_entities": [...],
     "current_states": {...},
     "theme": "dark|light|custom",
     "layout": "single|dual|triple column"
   }
   ```

5. **Generate Dashboard Code**:
   - Use `ai-visual-dashboard/dashboard_gen.py`
   - Pass context to selected LLM
   - Request HTML/CSS/JS output
   - Include responsive design
   - Add real-time state updates

6. **Dashboard Features to Include**:
   - Skeuomorphic design elements
   - Real-time entity state updates
   - Interactive controls (if applicable)
   - Status indicators
   - Appropriate visualizations (gauges, graphs, etc.)
   - Responsive layout
   - Theme-appropriate colors

7. **Save and Deploy**:
   - Save generated HTML to `ai-visual-dashboard/generated/`
   - Create timestamp-based filename
   - Set up WebSocket connection to HA
   - Enable live state updates

8. **Validate Output**:
   - Check HTML is valid
   - Verify all entities are accessible
   - Test WebSocket connection
   - Confirm responsive behavior
   - Validate accessibility

9. **Provide Access**:
   - Generate shareable URL
   - Create HA dashboard card integration
   - Provide embed code if requested

## Expected Outcome
- Custom visual dashboard generated
- Real-time entity state updates working
- Theme and layout match request
- Dashboard accessible via URL
- Integration with HA dashboard available

## Generation Options

**Themes**:
- Dark oceanic
- Light modern
- Retro skeuomorphic
- Minimalist
- High contrast

**Layouts**:
- Single column (mobile-first)
- Dual column (tablet/desktop)
- Triple column (wide desktop)
- Grid layout (custom)

**Visualizations**:
- Gauges (temperature, battery, etc.)
- Line charts (energy over time)
- Bar charts (consumption comparison)
- Status cards (on/off states)
- Maps (floor plans)

## Technical Details

**Backend**: `ai-visual-dashboard/dashboard_gen.py`
**HA Client**: `ai-visual-dashboard/ha_client.py`
**Output**: `ai-visual-dashboard/index.html` (or generated/[timestamp].html)

**Requirements**:
- Home Assistant long-lived access token
- WebSocket connection to HA
- LLM provider (Gemini or Ollama)

## Example Prompts

- "Energy dashboard with solar production focus"
- "Security overview with camera feeds and sensor status"
- "Climate control with all thermostats and weather"
- "Lighting scenes with color controls"
- "Minimal status board showing critical systems only"
