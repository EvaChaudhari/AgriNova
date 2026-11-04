"""Simple zero-dependency HTTP server to run the Krishi Mitra frontend."""

import http.server
import os
import socketserver
import sys
import webbrowser

PORT = 3000
DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")


class AgriFrontendHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Enable CORS and caching headers for local development
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()


# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def main():
    if not os.path.exists(DIRECTORY):
        print(f"Error: Directory '{DIRECTORY}' not found.", file=sys.stderr)
        sys.exit(1)

    port = PORT
    httpd = None
    for attempt_port in range(port, port + 10):
        try:
            httpd = ReusableTCPServer(("", attempt_port), AgriFrontendHandler)
            port = attempt_port
            break
        except OSError:
            continue

    if not httpd:
        print(f"Error: Could not bind to any port in range {PORT}-{PORT+10}", file=sys.stderr)
        sys.exit(1)

    url = f"http://localhost:{port}"
    print("=" * 60)
    print("Krishi Mitra (AgriNova) - Modern Frontend Server")
    print("=" * 60)
    print(f"  URL:         {url}")
    print(f"  Directory:   {DIRECTORY}")
    print(f"  Backend API: http://localhost:8000/api/v1")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 60)

    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping frontend server.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()

