#!/usr/bin/env python3
"""
Simplified server that bypasses Selenium Grid dependency for quick startup
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import json
import logging

# FastAPI imports
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Database imports
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

# Import from our modules
from models import Base, SessionLocal, Tender, save_tender_to_db, get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=SessionLocal().bind)

# FastAPI app setup
app = FastAPI(title="Canadian Procurement Scanner", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API endpoints
@app.get("/api/tenders")
async def get_tenders(
    skip: int = 0,
    limit: int = 100,
    portal: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get tenders with optional filtering"""
    query = db.query(Tender)
    
    # Only add portal filter if portal is not None
    if portal is not None:
        query = query.filter(Tender.portal == portal)
    query = query.filter(Tender.is_active.is_(True))
    query = query.order_by(desc(Tender.posted_date))
    
    total = query.count()
    tenders = list(query.offset(skip).limit(limit).all())
    
    return {
        "tenders": [
            {
                "id": t.id,
                "tender_id": t.tender_id,
                "title": t.title,
                "organization": t.organization,
                "portal": t.portal,
                "value": t.value,
                "closing_date": t.closing_date,
                "posted_date": t.posted_date,
                "description": t.description,
                "location": t.location,
                "categories": json.loads(str(t.categories)) if t.categories is not None else [],
                "keywords": json.loads(str(t.keywords)) if t.keywords is not None else [],
                "tender_url": t.tender_url,
                "matching_courses": json.loads(str(t.matching_courses)) if t.matching_courses is not None else [],
                "priority": t.priority
            }
            for t in tenders
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }

@app.get("/api/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """Get system statistics"""
    total_tenders = db.query(Tender).filter(Tender.is_active.is_(True)).count()
    total_value = db.query(func.sum(Tender.value)).filter(Tender.is_active.is_(True)).scalar() or 0
    
    # Portal breakdown
    portal_stats = db.query(
        Tender.portal,
        func.count(Tender.id).label('count'),
        func.sum(Tender.value).label('total_value')
    ).filter(Tender.is_active.is_(True)).group_by(Tender.portal).all()
    
    by_portal: list[Dict] = [
        {
            "portal": stat.portal,
            "count": stat.count,
            "total_value": float(stat.total_value or 0)
        }
        for stat in portal_stats
    ]
    
    # Closing soon (next 7 days)
    closing_soon = db.query(Tender).filter(
        Tender.closing_date.isnot(None),
        Tender.closing_date >= datetime.utcnow(),
        Tender.closing_date <= datetime.utcnow() + timedelta(days=7),
        Tender.is_active.is_(True)
    ).count()
    
    # New today
    today = datetime.utcnow().date()
    new_today = db.query(Tender).filter(
        Tender.posted_date.isnot(None),
        func.date(Tender.posted_date) == today,
        Tender.is_active.is_(True)
    ).count()
    
    return {
        "total_tenders": total_tenders,
        "total_value": float(total_value),
        "by_portal": by_portal,
        "closing_soon": closing_soon,
        "new_today": new_today,
        "last_scan": datetime.utcnow()
    }

@app.post("/api/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger a manual scan of all portals"""
    return {"message": "Scan functionality temporarily disabled - use full server for scraping"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Canadian Procurement Scanner API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting simplified procurement scanner API...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")