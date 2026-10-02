import subprocess
import sys
import time
import os

def free_port(port):
    try:
        output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
        for line in output.splitlines():
            parts = line.strip().split()
            if len(parts) > 4 and f":{port}" in parts[1] and "LISTENING" in line:
                pid = parts[-1]
                if pid and pid != "0" and pid != str(os.getpid()):
                    print(f"Freeing port {port} (stopping PID {pid})...")
                    subprocess.call(f"taskkill /F /PID {pid}", shell=True)
    except Exception:
        pass

print("Checking and freeing ports 8080 and 5173...")
free_port(8080)
free_port(5173)
time.sleep(1)

print("Starting Medix AI Backend Server on http://localhost:8080...")
backend_process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8080"],
    cwd=os.path.abspath(".")
)

time.sleep(2)

print("Starting Medix AI Frontend Server on http://localhost:5173...")
npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
frontend_process = subprocess.Popen(
    [npm_cmd, "run", "dev"],
    cwd=os.path.abspath(".")
)

print("\n=======================================================")
print("  MEDIX AI IS RUNNING!")
print("  Frontend UI : http://localhost:5173")
print("  Backend API : http://localhost:8080")
print("  API Docs    : http://localhost:8080/docs")
print("=======================================================\n")
print("Press Ctrl+C in the terminal to stop both servers.")

try:
    while True:
        time.sleep(1)
        if backend_process.poll() is not None or frontend_process.poll() is not None:
            print("One of the servers terminated unexpectedly.")
            break
except KeyboardInterrupt:
    print("\nStopping servers...")
finally:
    try:
        backend_process.terminate()
    except Exception:
        pass
    try:
        frontend_process.terminate()
    except Exception:
        pass
