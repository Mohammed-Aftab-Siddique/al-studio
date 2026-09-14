"""`al-studio-web` launcher with safe local port selection."""

import argparse
import socket
import threading
import webbrowser

import uvicorn

DEFAULT_PORT = 8177
FALLBACK_PORTS = range(8178, 8188)


def available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def choose_port(requested: int | None) -> int:
    ports = [requested] if requested is not None else [DEFAULT_PORT, *FALLBACK_PORTS]
    for port in ports:
        if available(port):
            return port
    raise RuntimeError("No free AL Studio Web port in 8177–8187; choose one with --port.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="al-studio-web")
    parser.add_argument("--port", type=int)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    port = choose_port(args.port)
    url = f"http://127.0.0.1:{port}"
    print(f"AL Studio Web is running at {url} (local only).")
    if not args.no_browser:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    uvicorn.run("app.web.app:app", host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
