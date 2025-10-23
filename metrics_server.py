#!/usr/bin/env python3
"""
Simple HTTP server to expose Prometheus metrics from files.
This server reads .prom files and serves them at /metrics endpoint.
"""

import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            self.serve_metrics()
        elif self.path == '/health':
            self.serve_health()
        else:
            self.send_error(404)
    
    def serve_metrics(self):
        """Serve metrics from .prom files."""
        try:
            # Read all .prom files from /metrics directory
            metrics_dir = Path('/metrics')
            metrics_content = []
            
            if metrics_dir.exists():
                for prom_file in metrics_dir.glob('*.prom'):
                    with open(prom_file, 'r') as f:
                        metrics_content.append(f.read())
            
            # Combine all metrics
            combined_metrics = '\n'.join(metrics_content)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(combined_metrics.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error reading metrics: {str(e)}")
    
    def serve_health(self):
        """Serve health check endpoint."""
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

def main():
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), MetricsHandler)
    print(f"Metrics server starting on port {port}")
    server.serve_forever()

if __name__ == '__main__':
    main()
