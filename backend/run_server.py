from pathlib import Path
import sys
import subprocess

HERE = Path(__file__).resolve().parent

def run():
    subprocess.check_call([
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload",
    ])

if __name__ == "__main__":
    sys.path.insert(0, str(HERE.parent))
    run()
