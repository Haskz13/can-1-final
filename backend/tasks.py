# backend/tasks.py
from celery import Celery
from celery.schedules import crontab
import os
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import pandas as pd
from pathlib import Path
from sqlalchemy import desc

# Import from models module (instead of main)
from models import SessionLocal, Tender, save_tender_to_db

# Import from main module (only what we need)
from main import (
    ProcurementScanner, 
    PORTAL_CONFIGS,
    TenderMatcher,
    TKA_COURSES,
    logger
)

# Import from scrapers module
from scrapers import (
    ProvincialScrapers,
    MunicipalScrapers,
    SpecializedScrapers,
    HealthEducationScrapers
)

# Updated dispatcher for new portal configurations
SCRAPER_DISPATCHER = {
    # --- Functions from main.py (called via the scanner instance) ---
    'canadabuys': 'scan_canadabuys',  # Now uses API
    'merx': 'scan_merx',
    'bcbid': 'scan_bcbid',
    'seao': 'scan_seao_web',  # Fixed: use scan_seao_web method
    'biddingo': 'scan_biddingo',
    'bidsandtenders': 'scan_bidsandtenders_portal',
    
    # bids&tenders platform cities
    'edmonton': 'scan_bidsandtenders_portal',
    'ottawa': 'scan_bidsandtenders_portal',
    'london': 'scan_bidsandtenders_portal',
    'hamilton': 'scan_bidsandtenders_portal',
    'kitchener': 'scan_bidsandtenders_portal',

    # --- Functions from scrapers.py (called as static methods) ---
    
    # Provincial Portals
    'albertapurchasing': ProvincialScrapers.scan_alberta_purchasing,
    'sasktenders': ProvincialScrapers.scan_saskatchewan_tenders,
    'manitoba': ProvincialScrapers.scan_manitoba_tenders,
    'ontario': ProvincialScrapers.scan_ontario_tenders,
    'ns': ProvincialScrapers.scan_ns_tenders,
    
    # Municipal Portals
    'calgary': MunicipalScrapers.scan_calgary_procurement,
    'winnipeg': MunicipalScrapers.scan_winnipeg_bids,
    'vancouver': MunicipalScrapers.scan_vancouver_procurement,
    'halifax': MunicipalScrapers.scan_halifax_procurement,
    'regina': MunicipalScrapers.scan_regina_procurement,

    # Specialized Portals
    'nbon': SpecializedScrapers.scan_nbon_newbrunswick,
    'pei': SpecializedScrapers.scan_pei_tenders,
    'nl': SpecializedScrapers.scan_nl_procurement,

    # Health & Education Portals
    'buybc': HealthEducationScrapers.scan_buybc_health,
    'mohltc': HealthEducationScrapers.scan_ontario_health,

    # Portals that are aliases of others (handled by their primary scraper type)
    'montreal': 'seao',  # Montreal uses SEAO
    'quebec_city': 'seao',  # Quebec City uses SEAO
    'saskatoon': 'sasktenders'  # Saskatoon uses SaskTenders
}

# Configure Celery
app = Celery(
    'procurement_scanner',
    broker=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://redis:6379/0')
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Toronto',
    enable_utc=True,
)

# Configure periodic tasks
app.conf.beat_schedule = {
    'scan-all-portals-hourly': {
        'task': 'tasks.scan_all_portals_task',
        'schedule': crontab(minute=0),
    },
    'scan-high-priority-frequent': {
        'task': 'tasks.scan_high_priority_portals',
        'schedule': crontab(minute='*/15'),
    },
    'scan-api-portals-frequent': {
        'task': 'tasks.scan_api_portals',
        'schedule': crontab(minute='*/30'),
    },
    'scan-municipal-morning': {
        'task': 'tasks.scan_municipal_portals',
        'schedule': crontab(hour=7, minute=30),
    },
    'scan-provincial-afternoon': {
        'task': 'tasks.scan_provincial_portals',
        'schedule': crontab(hour=13, minute=30),
    },
    'clean-expired-tenders': {
        'task': 'tasks.clean_expired_tenders',
        'schedule': crontab(hour=2, minute=0),
    },
    'generate-daily-report': {
        'task': 'tasks.generate_daily_report',
        'schedule': crontab(hour=7, minute=0),
    },
    'generate-weekly-summary': {
        'task': 'tasks.generate_weekly_summary',
        'schedule': crontab(day_of_week=1, hour=8, minute=0),
    },
    'backup-database': {
        'task': 'tasks.backup_database',
        'schedule': crontab(hour=3, minute=0),
    },
    'analyze-tender-trends': {
        'task': 'tasks.analyze_tender_trends',
        'schedule': crontab(day_of_week=0, hour=9, minute=0),
    }
}


def _process_tenders(tenders: List[Dict], portal_name: str, results: Dict, matcher: TenderMatcher):
    """Process and save tenders to database using the helper function from main."""
    if not tenders:
        return

    db = SessionLocal()
    portal_results = results['by_portal'].get(portal_name, {'found': 0, 'new': 0, 'updated': 0})
    portal_results['found'] += len(tenders)
    
    try:
        for tender_data in tenders:
            tender_data['matching_courses'] = matcher.match_courses(tender_data)
            tender_data['priority'] = matcher.calculate_priority(tender_data)

            was_new = save_tender_to_db(db, tender_data)

            if was_new:
                portal_results['new'] += 1
                results['new_tenders'] += 1
            else:
                portal_results['updated'] += 1
                results['updated_tenders'] += 1

        results['total_found'] += len(tenders)
        results['by_portal'][portal_name] = portal_results
    except Exception as e:
        logger.error(f"Error processing tenders for {portal_name}: {e}")
    finally:
        db.close()


async def _execute_scans_async(scanner: ProcurementScanner, portal_ids: List[str], results: Dict, matcher: TenderMatcher):
    """
    The async helper that iterates through portals and calls the correct scraper function.
    """
    driver = None
    session = SessionLocal()  # Use SessionLocal for DB session
    
    for portal_id in portal_ids:
        if portal_id not in PORTAL_CONFIGS:
            logger.warning(f"Configuration for portal_id '{portal_id}' not found. Skipping.")
            continue

        config = PORTAL_CONFIGS[portal_id]
        portal_type = config.get('type')
        scraper_func_ref = SCRAPER_DISPATCHER.get(portal_id)

        # Handle special portal types
        if portal_type == 'api':
            # API-based portals like CanadaBuys
            try:
                logger.info(f"Scanning {config['name']} via API")
                tenders = await scanner.scan_canadabuys()
                if tenders:
                    _process_tenders(tenders, config['name'], results, matcher)
                # Ensure results['scanned'] and results['errors'] are lists before appending
                if not isinstance(results['scanned'], list):
                    results['scanned'] = []
                results['scanned'].append(portal_id)
            except Exception as e:
                logger.error(f"Error scanning {config['name']} API: {e}")
                # Ensure results['errors'] is a list before appending
                if not isinstance(results['errors'], list):
                    results['errors'] = []
                results['errors'].append({'portal': config['name'], 'error': str(e)})
            continue
            
        elif portal_type == 'bidsandtenders':
            # bids&tenders platform
            try:
                logger.info(f"Scanning {config['name']} via bids&tenders platform")
                tenders = await scanner.scan_bidsandtenders_portal(config['name'], config['search_url'])  # type: ignore[arg-type]
                if tenders:
                    _process_tenders(tenders, config['name'], results, matcher)  # type: ignore[arg-type]
                # Ensure results['scanned'] and results['errors'] are lists before appending
                if not isinstance(results['scanned'], list):
                    results['scanned'] = []
                results['scanned'].append(portal_id)
            except Exception as e:
                logger.error(f"Error scanning {config['name']}: {e}")
                # Ensure results['errors'] is a list before appending
                if not isinstance(results['errors'], list):
                    results['errors'] = []
                results['errors'].append({'portal': config['name'], 'error': str(e)})  # type: ignore[arg-type]
            continue

        # Handle dispatcher-based scrapers
        if isinstance(scraper_func_ref, str) and scraper_func_ref in SCRAPER_DISPATCHER:
            scraper_func_ref = SCRAPER_DISPATCHER.get(scraper_func_ref)
            
        if not callable(scraper_func_ref):
            logger.warning(f"No valid scraper function found for portal_id: {portal_id}")
            continue

        try:
            logger.info(f"Scanning portal: {config['name']}")
            tenders = []
            
            if config.get('requires_selenium', False):
                if driver is None:
                    driver = scanner.selenium.create_driver()
                
                # Check if the function is a method of the scanner instance
                if hasattr(scanner, scraper_func_ref.__name__):
                    method_to_call = getattr(scanner, scraper_func_ref.__name__)
                    # Handle methods that need extra arguments
                    if scraper_func_ref.__name__ in ['scan_ariba_portal', 'scan_biddingo']:
                         tenders = await method_to_call(config['name'], config)
                    else:
                        tenders = await method_to_call()
                else: # Static method from scrapers.py
                    tenders = await scraper_func_ref(driver, scanner.selenium)  # type: ignore[operator]
            else: # Non-selenium static method
                tenders = await scraper_func_ref(session)  # type: ignore[operator]
            
            if tenders:
                 _process_tenders(tenders, config['name'], results, matcher)  # type: ignore[arg-type]
            # Ensure results['scanned'] and results['errors'] are lists before appending
            if not isinstance(results['scanned'], list):
                results['scanned'] = []
            results['scanned'].append(portal_id)

        except Exception as e:
            logger.error(f"Error scanning {config['name']}: {e}", exc_info=True)
            # Ensure results['errors'] is a list before appending
            if not isinstance(results['errors'], list):
                results['errors'] = []
            results['errors'].append({'portal': config['name'], 'error': str(e)})  # type: ignore[arg-type]
        
    if driver:
        driver.quit()
    session.close()


@app.task(bind=True, max_retries=3)
def scan_specific_portals_task(self, portal_ids: List[str]):
    """The new master task that scans a specific list of portals using the dispatcher."""
    scanner = ProcurementScanner()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    results = {'scanned': [], 'total_found': 0, 'new_tenders': 0, 'updated_tenders': 0, 'errors': [], 'by_portal': {}}
    matcher = TenderMatcher()
    
    try:
        loop.run_until_complete(
            _execute_scans_async(scanner, portal_ids, results, matcher)
        )
    except Exception as e:
        logger.error(f"Fatal error in scan_specific_portals task: {e}")
        self.retry(countdown=300)
    finally:
        loop.close()
        
    return results


@app.task
def scan_all_portals_task():
    """Scan all configured portals."""
    all_portal_ids = list(PORTAL_CONFIGS.keys())
    return scan_specific_portals_task.delay(all_portal_ids)  # type: ignore[attr-defined]


@app.task
def scan_high_priority_portals():
    """Scan only high-traffic portals more frequently."""
    high_priority_ids = ['canadabuys', 'merx', 'toronto', 'ontario', 'bcbid', 'seao']
    return scan_specific_portals_task.delay(high_priority_ids)  # type: ignore[attr-defined]


@app.task
def scan_api_portals():
    """Scan portals with API access for real-time updates."""
    api_portal_ids = [k for k,v in PORTAL_CONFIGS.items() if v.get('type') in ['api', 'api_and_scrape']]
    return scan_specific_portals_task.delay(api_portal_ids)  # type: ignore[attr-defined]


@app.task
def scan_municipal_portals():
    """Scan all municipal portals."""
    municipal_ids = [k for k,v in PORTAL_CONFIGS.items() if 'City of' in v['name'] or 'Municipality' in v['name']]
    return scan_specific_portals_task.delay(municipal_ids)  # type: ignore[attr-defined]


@app.task
def scan_provincial_portals():
    """Scan all provincial portals."""
    provincial_keywords = ['Province', 'Provincial', 'Government', 'Tenders', 'Purchasing Connection', 'Opportunities Network']
    provincial_ids = [k for k,v in PORTAL_CONFIGS.items() 
                      if any(keyword in v['name'] for keyword in provincial_keywords) 
                      and 'City' not in v['name']]
    return scan_specific_portals_task.delay(provincial_ids)  # type: ignore[attr-defined]


@app.task
def clean_expired_tenders():
    """Mark expired tenders as inactive and clean old data."""
    db = SessionLocal()
    try:
        expired_count = db.query(Tender).filter(
            Tender.closing_date < datetime.utcnow(),
            Tender.is_active == True
        ).update({'is_active': False}, synchronize_session=False)
        
        old_date = datetime.utcnow() - timedelta(days=180)
        deleted_count = db.query(Tender).filter(
            Tender.closing_date < old_date,
            Tender.is_active == False
        ).delete(synchronize_session=False)
        
        db.commit()
        logger.info(f"Cleaned expired tenders. Deactivated: {expired_count}, Deleted old: {deleted_count}")
        return {'deactivated': expired_count, 'deleted': deleted_count}
    except Exception as e:
        logger.error(f"Error cleaning expired tenders: {e}")
        db.rollback()
    finally:
        db.close()


@app.task
def generate_daily_report():
    """Generate and email daily procurement report"""
    db = SessionLocal()
    try:
        # Get today's statistics
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # New tenders today
        new_today = db.query(Tender).filter(
            Tender.posted_date.isnot(None),  # type: ignore[reportAttributeAccessIssue]
            Tender.posted_date >= today_start
        ).all()
        
        # Closing soon (next 3 days)
        closing_soon = db.query(Tender).filter(
            Tender.is_active == True,
            Tender.closing_date.isnot(None),  # type: ignore[reportAttributeAccessIssue]
            Tender.closing_date <= datetime.utcnow() + timedelta(days=3),
            Tender.closing_date > datetime.utcnow()
        ).order_by(Tender.closing_date).all()
        
        # High priority tenders
        high_priority = db.query(Tender).filter(
            Tender.is_active == True,
            Tender.priority == 'high'
        ).order_by(desc(Tender.value)).limit(10).all()
        
        # Generate report content
        report_html = generate_report_html(new_today, closing_soon, high_priority)
        
        # Send email if configured
        if os.getenv('SMTP_HOST') and os.getenv('REPORT_RECIPIENTS'):
            send_email_report(
                subject=f"Daily Procurement Report - {datetime.now().strftime('%Y-%m-%d')}",
                body=report_html,
                recipients=os.getenv('REPORT_RECIPIENTS').split(',')  # type: ignore[attr-defined]
            )
            
        return {
            'new_tenders': len(new_today),
            'closing_soon': len(closing_soon),
            'high_priority': len(high_priority)
        }
        
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
    finally:
        db.close()


def generate_report_html(new_tenders, closing_soon, high_priority):
    """Generate HTML report content"""
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #34495e; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #3498db; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .high {{ color: #e74c3c; font-weight: bold; }}
            .medium {{ color: #f39c12; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>Daily Procurement Intelligence Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        
        <h2>Summary</h2>
        <ul>
            <li>New Tenders Today: {len(new_tenders)}</li>
            <li>Closing Soon (Next 3 Days): {len(closing_soon)}</li>
            <li>High Priority Opportunities: {len(high_priority)}</li>
        </ul>
        
        <h2>New Tenders Posted Today</h2>
        {generate_tender_table(new_tenders)}
        
        <h2>Tenders Closing Soon</h2>
        {generate_tender_table(closing_soon)}
        
        <h2>High Priority Opportunities</h2>
        {generate_tender_table(high_priority)}
        
        <p><em>This is an automated report from the Canadian Procurement Intelligence Scanner</em></p>
    </body>
    </html>
    """
    return html


def generate_tender_table(tenders):
    """Generate HTML table from tenders"""
    if not tenders:
        return "<p>No tenders in this category.</p>"
        
    rows = []
    for tender in tenders:
        priority_class = tender.priority if tender.priority in ['high', 'medium'] else ''
        matching_courses = json.loads(tender.matching_courses) if tender.matching_courses else []
        
        rows.append(f"""
        <tr>
            <td>{tender.tender_id}</td>
            <td>{tender.title}</td>
            <td>{tender.organization}</td>
            <td>{tender.portal}</td>
            <td>${tender.value:,.0f}</td>
            <td>{tender.closing_date.strftime('%Y-%m-%d') if tender.closing_date else 'N/A'}</td>
            <td class="{priority_class}">{tender.priority.upper()}</td>
            <td>{', '.join(matching_courses[:2])}</td>
        </tr>
        """)
        
    return f"""
    <table>
        <tr>
            <th>Tender ID</th>
            <th>Title</th>
            <th>Organization</th>
            <th>Portal</th>
            <th>Value</th>
            <th>Closing Date</th>
            <th>Priority</th>
            <th>Matching Courses</th>
        </tr>
        {''.join(rows)}
    </table>
    """


def send_email_report(subject, body, recipients):
    """Send email report"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = os.getenv('SMTP_USER')
        msg['To'] = ', '.join(recipients)
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(os.getenv('SMTP_HOST'), int(os.getenv('SMTP_PORT', 587))) as server:
            server.starttls()
            server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
            server.send_message(msg)
            
        logger.info(f"Report sent to {len(recipients)} recipients")
    except Exception as e:
        logger.error(f"Error sending email report: {e}")


@app.task
def generate_weekly_summary():
    """Generate weekly summary report"""
    db = SessionLocal()
    try:
        week_start = datetime.utcnow() - timedelta(days=7)
        
        # Get weekly statistics
        weekly_stats = {
            'total_new': db.query(Tender).filter(
                Tender.posted_date.isnot(None),  # type: ignore[reportAttributeAccessIssue]
                Tender.posted_date >= week_start
            ).count(),
            'total_closed': db.query(Tender).filter(
                Tender.closing_date.isnot(None),  # type: ignore[reportAttributeAccessIssue]
                Tender.closing_date >= week_start,
                Tender.closing_date < datetime.utcnow()
            ).count(),
            'by_portal': db.query(
                Tender.portal,
                func.count(Tender.id).label('count')
            ).filter(
                Tender.posted_date.isnot(None),  # type: ignore[reportAttributeAccessIssue]
                Tender.posted_date >= week_start
            ).group_by(Tender.portal).all(),
            'by_category': {}
        }
        
        # Analyze categories
        tenders = db.query(Tender).filter(
            Tender.posted_date.isnot(None),  # type: ignore[reportAttributeAccessIssue]
            Tender.posted_date >= week_start
        ).all()
        category_counts = {}
        for tender in tenders:
            if tender.categories:
                categories = json.loads(tender.categories)
                for cat in categories:
                    category_counts[cat] = category_counts.get(cat, 0) + 1
        
        weekly_stats['by_category'] = category_counts
        
        logger.info(f"Weekly summary: {weekly_stats['total_new']} new tenders from {len(weekly_stats['by_portal'])} portals")
        return weekly_stats
        
    except Exception as e:
        logger.error(f"Error generating weekly summary: {e}")
    finally:
        db.close()


@app.task
def backup_database():
    """Backup database to file"""
    try:
        backup_dir = Path("/app/data/backups")
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f"procurement_backup_{timestamp}.sql"
        
        # Use pg_dump for PostgreSQL backup
        import subprocess
        db_url = os.getenv('DATABASE_URL', '')
        
        # Parse database URL
        import re
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
        if match:
            user, password, host, port, dbname = match.groups()
            
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            cmd = [
                'pg_dump',
                '-h', host,
                '-p', port,
                '-U', user,
                '-d', dbname,
                '-f', str(backup_file)
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Database backed up to {backup_file}")
                
                # Clean old backups (keep last 7)
                backups = sorted(backup_dir.glob('procurement_backup_*.sql'))
                if len(backups) > 7:
                    for old_backup in backups[:-7]:
                        old_backup.unlink()
                        
                return {'status': 'success', 'file': str(backup_file)}
            else:
                logger.error(f"Backup failed: {result.stderr}")
                return {'status': 'failed', 'error': result.stderr}
                
    except Exception as e:
        logger.error(f"Error during backup: {e}")
        return {'status': 'failed', 'error': str(e)}


@app.task
def analyze_tender_trends():
    """Analyze procurement trends over time"""
    db = SessionLocal()
    try:
        # Last 30 days analysis
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        trends: Dict[str, Any] = {
            'daily_counts': [],
            'portal_trends': {},
            'category_trends': {},
            'value_trends': [],
            'top_organizations': []
        }
        
        # Daily tender counts
        for i in range(30):
            day = start_date + timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0)
            day_end = day_start + timedelta(days=1)
            
            count = db.query(Tender).filter(
                Tender.posted_date.isnot(None),  # type: ignore[reportAttributeAccessIssue]
                Tender.posted_date >= day_start,
                Tender.posted_date < day_end
            ).count()
            
            trends['daily_counts'].append({
                'date': day.strftime('%Y-%m-%d'),
                'count': count
            })
        
        # Top organizations by tender count
        top_orgs = db.query(
            Tender.organization,
            func.count(Tender.id).label('count')
        ).filter(
            Tender.posted_date.isnot(None),  # type: ignore[reportAttributeAccessIssue]
            Tender.posted_date >= start_date
        ).group_by(Tender.organization).order_by(desc(func.count(Tender.id))).limit(10).all()
        
        trends['top_organizations'] = [{'org': org, 'count': count} for org, count in top_orgs]
        
        logger.info(f"Trend analysis complete. Found {sum(d['count'] for d in trends['daily_counts'])} tenders in last 30 days")
        return trends
        
    except Exception as e:
        logger.error(f"Error analyzing trends: {e}")
    finally:
        db.close() 