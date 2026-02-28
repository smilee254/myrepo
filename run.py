
import subprocess
import time
import sys

import os

def kill_ghosts():
    print("🧹 Cleaning up ghost processes on ports 8501/8502/8503/8000...")
    os.system("pkill -9 -f 'streamlit run'")
    os.system("pkill -9 -f 'uvicorn'")
    time.sleep(1)

def start_idcs():
    kill_ghosts()
    print("🚀 Starting IDCS System...")

    # 1. Start the FastAPI Backend
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    print("✅ Backend initiating on http://127.0.0.1:8000")

    # Give the backend 2 seconds to bind the port
    time.sleep(2)

    # 2. Start the Streamlit Frontend
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8503"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    print("✅ Frontend initiating on http://localhost:8503")

    print("\n💡 System is LIVE. Press Ctrl+C to shut down both.")

    try:
        # Keep the script running to monitor processes
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down safely...")
        backend_process.terminate()
        frontend_process.terminate()
        print("👋 Goodbye!")

if __name__ == "__main__":
    start_idcs()