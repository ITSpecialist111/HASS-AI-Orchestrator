import subprocess
import time
import requests
import sys
import os
import signal

def check_service(url, name, retries=30, delay=1):
    print(f"Checking {name} at {url}...")
    for i in range(retries):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"✅ {name} is UP!")
                return True
        except requests.ConnectionError:
            pass
        
        print(f"Waiting for {name}... ({i+1}/{retries})")
        time.sleep(delay)
    
    print(f"❌ {name} failed to start.")
    return False

def main():
    print("🚀 Starting E2E Verification...")
    
    # Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_dir = os.path.join(base_dir, "backend")
    dashboard_dir = os.path.join(base_dir, "dashboard")
    
    # Start Backend
    print("Starting Backend...")
    backend_cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8999"]
    backend_proc = subprocess.Popen(
        backend_cmd, 
        cwd=backend_dir,
        stdout=subprocess.DEVNULL, # Suppress output for cleaner log
        stderr=subprocess.PIPE
    )
    
    # Start Frontend
    print("Starting Frontend...")
    # Use 'npm.cmd' on Windows
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    frontend_cmd = [npm_cmd, "run", "dev"]
    frontend_proc = subprocess.Popen(
        frontend_cmd, 
        cwd=dashboard_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE
    )
    
    try:
        # Check Backend Health
        if not check_service("http://127.0.0.1:8999/docs", "Backend API"):
            raise RuntimeError("Backend failed to start")
            
        # Check Frontend Health
        # Vite usually starts on 5173, but it might perform port jumping. 
        # For this script we assume default or check the output if we were capturing it.
        # Simple check on default 5173
        if not check_service("http://localhost:5173", "Frontend Dashboard"):
             raise RuntimeError("Frontend failed to start")

        print("\n✨ E2E Verification PASSED! Both services started successfully.")
        
    except RuntimeError as e:
        print(f"\n❌ E2E Verification FAILED: {e}")
        # Print stderr if available
        if backend_proc.poll() is not None:
            print("Backend Error Output:")
            print(backend_proc.stderr.read().decode())
        if frontend_proc.poll() is not None:
             print("Frontend Error Output:")
             print(frontend_proc.stderr.read().decode())
        sys.exit(1)
        
    finally:
        print("\nShutting down services...")
        backend_proc.terminate()
        frontend_proc.terminate()
        
        # Windows doesn't always play nice with terminate() for shell-spawned processes like npm run dev
        if os.name == 'nt':
             subprocess.call(['taskkill', '/F', '/T', '/PID', str(frontend_proc.pid)])
             subprocess.call(['taskkill', '/F', '/T', '/PID', str(backend_proc.pid)])
        
        backend_proc.wait()
        frontend_proc.wait()
        print("Services stopped.")

if __name__ == "__main__":
    main()
