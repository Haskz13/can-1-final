#!/usr/bin/env python3
"""
Basic HTTP server using only Python standard library
"""
import http.server
import socketserver
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime

PORT = 8080

# Sample tender data
SAMPLE_TENDERS = [
    {
        "id": 1,
        "tender_id": "CAN-2024-001",
        "title": "Professional Development Training Services",
        "organization": "Government of Canada",
        "portal": "CanadaBuys",
        "value": 250000.0,
        "closing_date": "2024-01-15T23:59:59",
        "posted_date": "2023-12-15T10:00:00",
        "description": "Comprehensive professional development training program for government employees",
        "location": "Ottawa, ON",
        "categories": ["Training", "Professional Development"],
        "keywords": ["training", "professional development", "government"],
        "tender_url": "https://canadabuys.canada.ca/tender/001",
        "matching_courses": ["Leadership Development", "Project Management"],
        "priority": "high"
    },
    {
        "id": 2,
        "tender_id": "MERX-2024-002", 
        "title": "IT Security Training and Implementation",
        "organization": "City of Toronto",
        "portal": "MERX",
        "value": 180000.0,
        "closing_date": "2024-01-20T17:00:00",
        "posted_date": "2023-12-18T14:30:00",
        "description": "Cybersecurity training and system implementation services",
        "location": "Toronto, ON",
        "categories": ["IT Services", "Security Training"],
        "keywords": ["cybersecurity", "training", "implementation"],
        "tender_url": "https://merx.com/tender/002",
        "matching_courses": ["Cybersecurity Fundamentals", "IT Security Management"],
        "priority": "high"
    }
]

class APIHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {"status": "healthy", "timestamp": datetime.now().isoformat()}
            self.wfile.write(json.dumps(response).encode())
            
        elif path == '/api/tenders':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {
                "tenders": SAMPLE_TENDERS,
                "total": len(SAMPLE_TENDERS),
                "skip": 0,
                "limit": 100
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif path == '/api/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Calculate stats
            total_value = sum(t["value"] for t in SAMPLE_TENDERS)
            portals = {}
            for tender in SAMPLE_TENDERS:
                portal = tender["portal"]
                if portal not in portals:
                    portals[portal] = {"count": 0, "total_value": 0.0}
                portals[portal]["count"] += 1
                portals[portal]["total_value"] += tender["value"]
            
            by_portal = [
                {"portal": portal, "count": data["count"], "total_value": data["total_value"]}
                for portal, data in portals.items()
            ]
            
            response = {
                "total_tenders": len(SAMPLE_TENDERS),
                "total_value": total_value,
                "by_portal": by_portal,
                "closing_soon": 2,
                "new_today": 1,
                "last_scan": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response).encode())
            
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        self.send_cors_headers()
        
        if path == '/api/scan':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"message": "Mock scan initiated"}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_error(404, "Not Found")
    
    def do_OPTIONS(self):
        self.send_cors_headers()
        self.send_response(200)
        self.end_headers()
    
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), APIHandler) as httpd:
        print(f"🚀 Starting basic server on port {PORT}")
        print(f"📊 API: http://localhost:{PORT}/api/tenders")
        print(f"💓 Health: http://localhost:{PORT}/health")
        httpd.serve_forever()