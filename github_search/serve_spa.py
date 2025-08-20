#!/usr/bin/env python3
"""
Simple HTTP server to serve the Thrust Repository Viewer SPA
"""

import http.server
import socketserver
import webbrowser
import os
from threading import Timer

PORT = 8080

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to allow local file access
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def guess_type(self, path):
        # Ensure JSON files are served with correct content type
        if path.endswith('.json'):
            return 'application/json'
        return super().guess_type(path)

def open_browser():
    """Open the default web browser to the SPA"""
    webbrowser.open(f'http://localhost:{PORT}/thrust_repo_viewer.html')

def main():
    """Start the HTTP server and open browser"""
    # Change to the directory containing the files
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
        print(f"🚀 Thrust Repository Viewer Server")
        print(f"=" * 50)
        print(f"📡 Server running at: http://localhost:{PORT}")
        print(f"🌐 SPA URL: http://localhost:{PORT}/thrust_repo_viewer.html")
        print(f"📊 Data file: thrust_repos_with_stars_20250819_143818.json")
        print(f"🔗 Total repositories: 1408")
        print(f"=" * 50)
        print(f"💡 Opening browser automatically...")
        print(f"⏹️  Press Ctrl+C to stop the server")
        
        # Open browser after a short delay
        Timer(1.0, open_browser).start()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print(f"\n🛑 Server stopped by user")
            print(f"✅ Thanks for using Thrust Repository Viewer!")

if __name__ == "__main__":
    main()
