# models.py - Shared models and database functions
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, Boolean, Integer, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm.decl_api import DeclarativeMeta
from datetime import datetime
import json
import logging
from typing import List, Dict, Optional, Any, TYPE_CHECKING
import hashlib

if TYPE_CHECKING:
    from sqlalchemy.orm.decl_api import DeclarativeBase

logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = "postgresql://procurement_user:procurement_pass@postgres:5432/procurement_scanner"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base: Any = declarative_base()

class Tender(Base):
    __tablename__ = "tenders"
    
    id = Column(String, primary_key=True)
    tender_id = Column(String, unique=True, index=True)
    title = Column(String)
    organization = Column(String)
    portal = Column(String, index=True)
    portal_url = Column(String)
    value = Column(Float)
    closing_date = Column(DateTime, index=True)
    posted_date = Column(DateTime)
    description = Column(Text)
    location = Column(String)
    categories = Column(Text)  # JSON string
    keywords = Column(Text)  # JSON string
    contact_email = Column(String)
    contact_phone = Column(String)
    tender_url = Column(String)
    documents_url = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    hash = Column(String)  # To detect changes
    priority = Column(String)
    matching_courses = Column(Text)  # JSON string
    download_count = Column(Integer, default=0)
    attachments = Column(Text)  # JSON string of attachment info

def save_tender_to_db(db: Session, tender_data: Dict) -> bool:
    """Save tender to database, return True if new, False if updated"""
    try:
        # Generate hash for change detection
        content_hash = hashlib.md5(
            json.dumps(tender_data, sort_keys=True, default=str).encode()
        ).hexdigest()
        
        # Check if tender already exists
        existing_tender = db.query(Tender).filter(
            Tender.tender_id == tender_data['tender_id']
        ).first()
        
        if existing_tender:
            # Update existing tender if content changed
            current_hash = existing_tender.hash
            if current_hash is not None and str(current_hash) != content_hash:
                existing_tender.title = tender_data['title']
                existing_tender.organization = tender_data['organization']
                existing_tender.portal = tender_data['portal']
                existing_tender.portal_url = tender_data['portal_url']
                existing_tender.value = tender_data['value']
                existing_tender.closing_date = tender_data['closing_date']
                existing_tender.description = tender_data['description']
                existing_tender.location = tender_data['location']
                existing_tender.categories = json.dumps(tender_data.get('categories', []))
                existing_tender.keywords = json.dumps(tender_data.get('keywords', []))
                existing_tender.tender_url = tender_data['tender_url']
                existing_tender.documents_url = tender_data.get('documents_url', '')
                existing_tender.last_updated = datetime.utcnow()
                existing_tender.hash = content_hash
                existing_tender.priority = tender_data.get('priority', '')
                existing_tender.matching_courses = json.dumps(tender_data.get('matching_courses', []))
                
                db.commit()
                logger.info(f"Updating tender: {tender_data['tender_id']}")
                return False  # Not new
            return False  # No changes
        
        # Create new tender
        new_tender = Tender(
            id=tender_data['tender_id'],
            tender_id=tender_data['tender_id'],
            title=tender_data['title'],
            organization=tender_data['organization'],
            portal=tender_data['portal'],
            portal_url=tender_data['portal_url'],
            value=tender_data['value'],
            closing_date=tender_data['closing_date'],
            posted_date=tender_data.get('posted_date', datetime.utcnow()),
            description=tender_data['description'],
            location=tender_data.get('location', ''),
            categories=json.dumps(tender_data.get('categories', [])),
            keywords=json.dumps(tender_data.get('keywords', [])),
            tender_url=tender_data['tender_url'],
            documents_url=tender_data.get('documents_url', ''),
            hash=content_hash,
            priority=tender_data.get('priority', ''),
            matching_courses=json.dumps(tender_data.get('matching_courses', []))
        )
        
        db.add(new_tender)
        db.commit()
        logger.info(f"Adding new tender: {tender_data['tender_id']}")
        return True  # New tender
        
    except Exception as e:
        logger.error(f"Error saving tender {tender_data.get('tender_id', 'unknown')}: {e}")
        db.rollback()
        return False

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 