# config.py - Shared configuration and constants
import os
from typing import Dict, List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings using pydantic-settings for environment variable management"""
    
    # Database configuration
    DATABASE_URL: str = "sqlite:///./procurement_scanner.db"
    POSTGRES_USER: str = "procurement_user"
    POSTGRES_PASSWORD: str = "procurement_pass"
    POSTGRES_DB: str = "procurement_scanner"
    
    # Redis configuration
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Selenium configuration
    SELENIUM_HUB_URL: str = "http://selenium-hub:4444/wd/hub"
    SELENIUM_GRID_ENABLED: bool = True
    
    # API configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    
    # Frontend configuration
    REACT_APP_API_URL: str = "http://localhost:8000/api"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # Celery configuration
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    
    # MERX Portal Credentials (optional)
    MERX_USERNAME: str = ""
    MERX_PASSWORD: str = ""
    
    # Email Configuration (optional)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    
    # Monitoring
    ENABLE_METRICS: bool = True
    PROMETHEUS_PORT: int = 9090
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Create settings instance
settings = Settings()

# Legacy compatibility - keep the original constants
DATABASE_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL
SELENIUM_HUB_URL = settings.SELENIUM_HUB_URL

# Training courses for matching
TKA_COURSES = [
    "Project Management", "Leadership", "Communication", "Negotiation",
    "Contract Management", "Procurement", "Supply Chain", "Risk Management",
    "Strategic Planning", "Change Management", "Team Building", "Conflict Resolution",
    "Time Management", "Problem Solving", "Decision Making", "Financial Management",
    "Human Resources", "Marketing", "Sales", "Customer Service", "Quality Management",
    "Process Improvement", "Innovation", "Digital Transformation", "Data Analysis",
    "Business Intelligence", "Cybersecurity", "Cloud Computing", "Agile", "Scrum",
    "Lean Six Sigma", "ISO Standards", "Compliance", "Regulatory Affairs",
    "Environmental Management", "Sustainability", "Corporate Social Responsibility"
]

# Portal configurations
PORTAL_CONFIGS = {
    'canadabuys': {
        'name': 'CanadaBuys',
        'type': 'api',
        'url': 'https://canadabuys.canada.ca',
        'priority': 'high'
    },
    'merx': {
        'name': 'MERX',
        'type': 'web',
        'url': 'https://www.merx.com',
        'priority': 'high'
    },
    'bcbid': {
        'name': 'BC Bid',
        'type': 'web',
        'url': 'https://www.bcbid.gov.bc.ca',
        'priority': 'high'
    },
    'seao': {
        'name': 'SEAO Quebec',
        'type': 'web',
        'url': 'https://seao.gouv.qc.ca',
        'priority': 'high'
    },
    'biddingo': {
        'name': 'Biddingo',
        'type': 'web',
        'url': 'https://www.biddingo.com',
        'priority': 'medium'
    },
    'bidsandtenders': {
        'name': 'Bids&Tenders',
        'type': 'web',
        'url': 'https://www.bidsandtenders.ca',
        'priority': 'medium'
    },
    # Provincial Portals
    'albertapurchasing': {
        'name': 'Alberta Purchasing Connection',
        'type': 'web',
        'url': 'https://www.alberta.ca/purchasing-connection.aspx',
        'priority': 'high'
    },
    'sasktenders': {
        'name': 'Saskatchewan Tenders',
        'type': 'web',
        'url': 'https://www.sasktenders.ca',
        'priority': 'high'
    },
    'manitoba': {
        'name': 'Manitoba Tenders',
        'type': 'web',
        'url': 'https://www.gov.mb.ca/tenders',
        'priority': 'high'
    },
    'ontario': {
        'name': 'Ontario Tenders',
        'type': 'web',
        'url': 'https://www.ontario.ca/tenders',
        'priority': 'high'
    },
    'ns': {
        'name': 'Nova Scotia Tenders',
        'type': 'web',
        'url': 'https://novascotia.ca/tenders',
        'priority': 'high'
    },
    # Municipal Portals
    'calgary': {
        'name': 'City of Calgary Procurement',
        'type': 'web',
        'url': 'https://www.calgary.ca/procurement',
        'priority': 'medium'
    },
    'winnipeg': {
        'name': 'City of Winnipeg Bids',
        'type': 'web',
        'url': 'https://www.winnipeg.ca/bids',
        'priority': 'medium'
    },
    'vancouver': {
        'name': 'City of Vancouver Procurement',
        'type': 'web',
        'url': 'https://vancouver.ca/procurement',
        'priority': 'medium'
    },
    'halifax': {
        'name': 'City of Halifax Procurement',
        'type': 'web',
        'url': 'https://www.halifax.ca/procurement',
        'priority': 'medium'
    },
    'regina': {
        'name': 'City of Regina Procurement',
        'type': 'web',
        'url': 'https://www.regina.ca/procurement',
        'priority': 'medium'
    },
    # Specialized Portals
    'nbon': {
        'name': 'NBON New Brunswick',
        'type': 'web',
        'url': 'https://www.nbon.ca',
        'priority': 'medium'
    },
    'pei': {
        'name': 'PEI Tenders',
        'type': 'web',
        'url': 'https://www.princeedwardisland.ca/tenders',
        'priority': 'medium'
    },
    'nl': {
        'name': 'Newfoundland Procurement',
        'type': 'web',
        'url': 'https://www.gov.nl.ca/procurement',
        'priority': 'medium'
    },
    # Health & Education Portals
    'buybc': {
        'name': 'BuyBC Health',
        'type': 'web',
        'url': 'https://www.buybc.ca/health',
        'priority': 'medium'
    },
    'mohltc': {
        'name': 'Ontario Health',
        'type': 'web',
        'url': 'https://www.ontariohealth.ca/procurement',
        'priority': 'medium'
    },
    # Bids&Tenders Platform Cities
    'edmonton': {
        'name': 'City of Edmonton',
        'type': 'bidsandtenders',
        'url': 'https://www.bidsandtenders.ca',
        'search_url': 'https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=AB',
        'priority': 'medium'
    },
    'ottawa': {
        'name': 'City of Ottawa',
        'type': 'bidsandtenders',
        'url': 'https://www.bidsandtenders.ca',
        'search_url': 'https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=ON',
        'priority': 'medium'
    },
    'london': {
        'name': 'City of London',
        'type': 'bidsandtenders',
        'url': 'https://www.bidsandtenders.ca',
        'search_url': 'https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=ON',
        'priority': 'medium'
    },
    'hamilton': {
        'name': 'City of Hamilton',
        'type': 'bidsandtenders',
        'url': 'https://www.bidsandtenders.ca',
        'search_url': 'https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=ON',
        'priority': 'medium'
    },
    'kitchener': {
        'name': 'City of Kitchener',
        'type': 'bidsandtenders',
        'url': 'https://www.bidsandtenders.ca',
        'search_url': 'https://www.bidsandtenders.ca/section/opportunities/opportunities.asp?type=1&show=all&rregion=ON',
        'priority': 'medium'
    }
} 