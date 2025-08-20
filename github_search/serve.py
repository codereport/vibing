#!/usr/bin/env python3
"""
Simple HTTP server to serve the GitHub Search Hub and data files.
This resolves CORS issues when loading data files from the data/ directory.
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

PORT = 8080


class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to allow data loading
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()


def main():
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"🚀 Starting HTTP server on port {PORT}")
        print(f"📂 Serving files from: {os.getcwd()}")
        print(f"🔗 GitHub Search Hub: http://localhost:{PORT}/index.html")
        print(f"🚀 Thrust Repositories: http://localhost:{PORT}/thrust_repos.html")
        print(f"📊 Analysis Dashboard: http://localhost:{PORT}/thrust_usage.html")
        print(f"\n💡 Press Ctrl+C to stop the server")

        # Try to open the main page in browser
        try:
            webbrowser.open(f"http://localhost:{PORT}/index.html")
        except:
            pass

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print(f"\n🛑 Server stopped")


if __name__ == "__main__":
    main()
