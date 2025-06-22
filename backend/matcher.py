# matcher.py - Tender matching and priority calculation
import logging
from datetime import datetime
from typing import Dict, List
from config import TKA_COURSES

logger = logging.getLogger(__name__)

class TenderMatcher:
    """Match tenders to training courses and calculate priority"""
    
    @staticmethod
    def match_courses(tender: Dict) -> List[str]:
        """Match tender to relevant training courses"""
        text = f"{tender.get('title', '')} {tender.get('description', '')}".lower()
        matched_courses = []
        
        for course in TKA_COURSES:
            if course.lower() in text:
                matched_courses.append(course)
        
        return matched_courses
    
    @staticmethod
    def calculate_priority(tender: Dict) -> str:
        """Calculate tender priority based on various factors"""
        score = 0
        
        # Value-based scoring
        value = tender.get('value', 0)
        if value > 1000000:
            score += 5
        elif value > 500000:
            score += 3
        elif value > 100000:
            score += 2
        elif value > 50000:
            score += 1
        
        # Time-based scoring
        closing_date = tender.get('closing_date')
        if closing_date:
            if isinstance(closing_date, str):
                try:
                    closing_date = datetime.fromisoformat(closing_date.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    closing_date = None
            
            if closing_date:
                days_until_closing = (closing_date - datetime.utcnow()).days
                if days_until_closing <= 7:
                    score += 5
                elif days_until_closing <= 14:
                    score += 3
                elif days_until_closing <= 30:
                    score += 1
        
        # Portal-based scoring
        portal = tender.get('portal', '').lower()
        if 'canadabuys' in portal:
            score += 3
        elif 'merx' in portal:
            score += 2
        elif 'bcbid' in portal:
            score += 2
        
        # Course matching scoring
        if tender.get('matching_courses'):
            score += len(tender['matching_courses']) * 2
        
        # Determine priority
        if score >= 8:
            return 'high'
        elif score >= 5:
            return 'medium'
        else:
            return 'low' 