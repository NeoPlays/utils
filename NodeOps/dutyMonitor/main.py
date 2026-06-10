import subprocess
import threading
import signal
import sys
from monitor import monitor

gunicorn_proc = None

def shutdown(signum, frame):
    print("Received shutdown signal, exiting...")
    if gunicorn_proc and gunicorn_proc.poll() is None:
        gunicorn_proc.terminate()
        try:
            gunicorn_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            gunicorn_proc.kill()
    sys.exit(0)

def start_webserver():
    global gunicorn_proc
    gunicorn_proc = subprocess.Popen([
        "gunicorn", "--bind", "0.0.0.0:8080", "webserver:app"
    ])

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    t1 = threading.Thread(target=monitor, daemon=True)
    t2 = threading.Thread(target=start_webserver)

    t1.start()
    t2.start()

    t1.join()
    t2.join()
