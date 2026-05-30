import socket
import json
import threading

def send_clawd_status(status: str) -> None:
    """
    Sends a non-blocking TCP status update to the Clawd Tank simulator on localhost:19872.
    Spawns inside a daemon thread to prevent CLI latency or blocking in case the
    simulator is not currently running or listening.
    """
    def _send():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)  # Fast timeout (300ms) to ensure zero impact
                s.connect(("127.0.0.1", 19872))
                payload = json.dumps({"action": "set_status", "status": status}) + "\n"
                s.sendall(payload.encode("utf-8"))
        except Exception:
            # Fail silently and gracefully if the simulator is not running
            pass

    threading.Thread(target=_send, daemon=True).start()
