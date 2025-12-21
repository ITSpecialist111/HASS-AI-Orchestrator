
from starlette.types import ASGIApp, Receive, Scope, Send

class IngressMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "")
            headers = dict(scope.get("headers", []))
            
            # Extract X-Ingress-Path from headers (bytes to str)
            ingress_path = None
            for key, value in headers.items():
                if key.decode("latin-1").lower() == "x-ingress-path":
                    ingress_path = value.decode("latin-1")
                    break
            
            # Simple debug log (using print usually visible in HA Add-on logs)
            # print(f"DEBUG MIDDLEWARE: type={scope['type']} path={path} ingress={ingress_path}", flush=True)

            original_path = path
            
            # 1. Strip Ingress Path
            if ingress_path and path.startswith(ingress_path):
                path = path[len(ingress_path):]
                if not path.startswith("/"):
                    path = "/" + path

            # 2. Normalize Double Slashes (The fix for 405/WS crashes)
            while "//" in path:
                path = path.replace("//", "/")
            
            # 3. Handle Missing Trailing Slash (Critical for relative assets)
            # If we are at the root (empty or just /) and it came through Ingress,
            # we must ensure a trailing slash so ./assets/ works.
            if ingress_path and (path == "" or path == "/"):
                 # We don't redirect (to avoid loop), we just ensure the app sees /
                 path = "/"

            # 4. Asset Normalization
            # Force /assets/ to be relative to root for the static mount
            if "assets/" in path and not path.startswith("/assets/"):
                path = "/assets/" + path.split("assets/")[-1]

            # 5. WS Fallback & Normalization
            if scope["type"] == "websocket":
                if "/ws" in path:
                     path = "/ws"
                
                if path != original_path:
                    scope["path"] = path

            if path != original_path:
                print(f"DEBUG REWRITE: {original_path} -> {path} (Ingress: {ingress_path})", flush=True)
                scope["path"] = path
        
        await self.app(scope, receive, send)
