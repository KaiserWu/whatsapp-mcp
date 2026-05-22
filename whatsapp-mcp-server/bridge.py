import atexit
import os
import platform
import socket
import subprocess
import sys
import time

DATA_DIR = os.path.expanduser("~/.whatsapp-mcp")
STORE_DIR = os.path.join(DATA_DIR, "store")


def get_db_path() -> str:
    return os.path.join(STORE_DIR, "messages.db")


def get_store_db_path() -> str:
    return os.path.join(STORE_DIR, "whatsapp.db")


def is_authenticated() -> bool:
    return os.path.isfile(os.path.join(STORE_DIR, "whatsapp.db"))


def get_bridge_binary() -> str | None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        suffix = "darwin-arm64" if machine in ("arm64", "aarch64") else "darwin-amd64"
    elif system == "windows":
        suffix = "windows-amd64.exe"
    else:
        suffix = "linux-amd64"

    # Bundled binary (inside .dxt package)
    bundled = os.path.join(script_dir, "bin", f"whatsapp-bridge-{suffix}")
    if os.path.isfile(bundled):
        return bundled

    # Development fallback: compiled binary in source tree
    dev = os.path.abspath(os.path.join(script_dir, "..", "whatsapp-bridge", "whatsapp-client"))
    if os.path.isfile(dev):
        return dev

    return None


_bridge_process: subprocess.Popen | None = None


def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_bridge() -> subprocess.Popen | None:
    global _bridge_process

    if _is_port_in_use(8080):
        return None

    binary = get_bridge_binary()
    if not binary:
        print(
            "WARNING: Go bridge binary not found. "
            "Run build-dxt.sh to build it, or start whatsapp-bridge manually.",
            file=sys.stderr,
        )
        return None

    if platform.system() != "Windows":
        os.chmod(binary, 0o755)

    os.makedirs(STORE_DIR, exist_ok=True)

    # Create a symlink in DATA_DIR so users can run the binary from a stable path
    symlink_path = os.path.join(DATA_DIR, os.path.basename(binary))
    if not os.path.exists(symlink_path):
        try:
            os.symlink(binary, symlink_path)
        except Exception:
            pass

    log_path = os.path.join(DATA_DIR, "bridge.log")
    log_file = open(log_path, "a")

    try:
        _bridge_process = subprocess.Popen(
            [binary],
            cwd=DATA_DIR,
            stdout=log_file,
            stderr=log_file,
        )
    except Exception as exc:
        print(f"Failed to start Go bridge: {exc}", file=sys.stderr)
        log_file.close()
        return None

    # Give the bridge time to bind port 8080
    time.sleep(2)

    if _bridge_process.poll() is not None:
        print(
            f"Go bridge exited unexpectedly. Check {log_path} for details.",
            file=sys.stderr,
        )
        log_file.close()
        return None

    atexit.register(stop_bridge)
    return _bridge_process


def stop_bridge() -> None:
    global _bridge_process
    if _bridge_process and _bridge_process.poll() is None:
        _bridge_process.terminate()
        try:
            _bridge_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _bridge_process.kill()
    _bridge_process = None
