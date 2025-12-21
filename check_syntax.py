import ast
import traceback
import sys

files = [
    "C:\\Users\\graham\\Documents\\GitHub\\HASS-AI-Orchestrator\\ai-orchestrator\\backend\\agents\\base_agent.py",
    "C:\\Users\\graham\\Documents\\GitHub\\HASS-AI-Orchestrator\\ai-orchestrator\\backend\\agents\\architect_agent.py"
]

has_error = False

for file_path in files:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        ast.parse(content)
        print(f"Syntax OK: {file_path}")
    except SyntaxError as e:
        has_error = True
        print(f"❌ Syntax Error in {file_path}: {e}")
        # Print context
        lines = content.splitlines()
        if e.lineno:
            start = max(0, e.lineno - 5)
            end = min(len(lines), e.lineno + 5)
            for i in range(start, end):
                prefix = ">> " if i + 1 == e.lineno else "   "
                print(f"{prefix}{i+1}: {lines[i]}")
    except Exception as e:
        has_error = True
        print(f"❌ Error reading {file_path}: {e}")
        traceback.print_exc()

sys.exit(1 if has_error else 0)
