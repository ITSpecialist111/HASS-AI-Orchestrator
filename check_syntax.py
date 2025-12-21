import ast
import traceback

file_path = "C:\\Users\\graham\\Documents\\GitHub\\HASS-AI-Orchestrator\\ai-orchestrator\\backend\\mcp_server.py"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    ast.parse(content)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax Error: {e}")
    # Print context
    lines = content.splitlines()
    if e.lineno:
        start = max(0, e.lineno - 5)
        end = min(len(lines), e.lineno + 5)
        for i in range(start, end):
            prefix = ">> " if i + 1 == e.lineno else "   "
            print(f"{prefix}{i+1}: {lines[i]}")
except Exception as e:
    traceback.print_exc()
