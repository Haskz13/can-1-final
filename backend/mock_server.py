#!/usr/bin/env python3
"""
Mock server with sample data for Canadian Procurement Scanner
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import Optional
import random

app = FastAPI(title="Canadian Procurement Scanner", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    },
    {
        "id": 3,
        "tender_id": "BC-2024-003",
        "title": "Change Management Consulting Services",
        "organization": "Province of British Columbia",
        "portal": "BC Bid",
        "value": 120000.0,
        "closing_date": "2024-01-25T16:00:00",
        "posted_date": "2023-12-20T09:15:00",
        "description": "Organizational change management and training services",
        "location": "Vancouver, BC",
        "categories": ["Consulting", "Change Management"],
        "keywords": ["change management", "consulting", "organizational development"],
        "tender_url": "https://bcbid.gov.bc.ca/tender/003",
        "matching_courses": ["Change Management Certification", "Organizational Development"],
        "priority": "medium"
    },
    {
        "id": 4,
        "tender_id": "QC-2024-004",
        "title": "Formation en gestion de projet",
        "organization": "Gouvernement du Québec",
        "portal": "SEAO",
        "value": 95000.0,
        "closing_date": "2024-01-30T15:30:00",
        "posted_date": "2023-12-22T11:45:00",
        "description": "Services de formation en gestion de projet pour les employés gouvernementaux",
        "location": "Québec, QC",
        "categories": ["Formation", "Gestion de projet"],
        "keywords": ["formation", "gestion de projet", "certification"],
        "tender_url": "https://seao.ca/tender/004",
        "matching_courses": ["PMP Certification", "Agile Project Management"],
        "priority": "medium"
    },
    {
        "id": 5,
        "tender_id": "AB-2024-005",
        "title": "Digital Transformation Training Program",
        "organization": "Government of Alberta",
        "portal": "Alberta Purchasing",
        "value": 320000.0,
        "closing_date": "2024-02-05T17:00:00",
        "posted_date": "2023-12-28T10:00:00",
        "description": "Comprehensive digital transformation training and implementation support",
        "location": "Calgary, AB",
        "categories": ["Digital Transformation", "Training"],
        "keywords": ["digital transformation", "training", "implementation"],
        "tender_url": "https://vendor.purchasingconnection.ca/tender/005",
        "matching_courses": ["Digital Leadership", "Cloud Computing", "Data Analytics"],
        "priority": "high"
    }
]

@app.get("/api/tenders")
async def get_tenders(
    skip: int = 0,
    limit: int = 100,
    portal: Optional[str] = None
):
    """Get tenders with optional filtering"""
    tenders = SAMPLE_TENDERS
    
    if portal:
        tenders = [t for t in tenders if t["portal"] == portal]
    
    total = len(tenders)
    tenders = tenders[skip:skip + limit]
    
    return {
        "tenders": tenders,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@app.get("/api/stats")
async def get_statistics():
    """Get system statistics"""
    portals = {}
    total_value = 0
    
    for tender in SAMPLE_TENDERS:
        portal = tender["portal"]
        value = float(tender["value"])
        
        if portal not in portals:
            portals[portal] = {"count": 0, "total_value": 0.0}
        
        portals[portal]["count"] += 1
        portals[portal]["total_value"] += value
        total_value += value
    
    by_portal = [
        {
            "portal": portal,
            "count": data["count"],
            "total_value": data["total_value"]
        }
        for portal, data in portals.items()
    ]
    
    return {
        "total_tenders": len(SAMPLE_TENDERS),
        "total_value": total_value,
        "by_portal": by_portal,
        "closing_soon": 2,  # Mock data
        "new_today": 1,     # Mock data
        "last_scan": datetime.now().isoformat()
    }

@app.post("/api/scan")
async def trigger_scan():
    """Trigger a manual scan"""
    return {"message": "Mock scan initiated - in real app this would scrape procurement portals"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Canadian Procurement Scanner - Mock API", 
        "status": "running",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Canadian Procurement Scanner Mock API...")
    print("📊 Dashboard: http://localhost:3000")
    print("🔗 API Docs: http://localhost:8080/docs")
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")