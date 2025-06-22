# Canadian Procurement Scanner

A comprehensive procurement intelligence system that monitors multiple Canadian government procurement portals for training and professional development opportunities.

## 🚀 Quick Start

### Prerequisites
- Docker Desktop (Windows/Mac/Linux)
- 8GB+ RAM recommended
- Stable internet connection

### Automated Setup (Recommended)
```bash
# Windows
setup.bat

# Linux/Mac
chmod +x setup.sh
./setup.sh
```

### Manual Setup
1. **Start Docker Desktop**
2. **Copy environment file:**
   ```bash
   cp env.example .env
   ```
3. **Build and start services:**
   ```bash
   docker-compose up --build -d
   ```
4. **Wait for services to start (30-60 seconds)**
5. **Access the application:**
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## 🏗️ Architecture

### Backend Services
- **FastAPI**: REST API with async support
- **PostgreSQL**: Primary database
- **Redis**: Caching and task queue
- **Celery**: Background task processing
- **Selenium Grid**: Web scraping infrastructure

### Frontend
- **React 18**: Modern UI framework
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **Lucide React**: Icons

### Monitored Portals
- **Federal**: CanadaBuys, MERX
- **Provincial**: BC Bid, SEAO Quebec, Alberta Purchasing
- **Municipal**: Calgary, Vancouver, Winnipeg, Halifax
- **Specialized**: Biddingo, Bids&Tenders, Health/Education portals

## 🔧 Configuration

### Environment Variables
Copy `env.example` to `.env` and customize:

```bash
# Database
POSTGRES_USER=procurement_user
POSTGRES_PASSWORD=procurement_pass
POSTGRES_DB=procurement_scanner

# API
API_HOST=0.0.0.0
API_PORT=8000

# Frontend
REACT_APP_API_URL=http://localhost:8000/api
```

### Portal Configuration
Edit `backend/main.py` to add/modify portal configurations:

```python
PORTAL_CONFIGS = {
    'portal_name': {
        'name': 'Portal Display Name',
        'type': 'web|api',
        'url': 'https://portal-url.com',
        'priority': 'high|medium|low'
    }
}
```

## 📊 Features

### Real-time Monitoring
- Automated scanning of 20+ procurement portals
- Intelligent tender matching with course relevance
- Priority scoring based on value and deadline
- Change detection and updates

### Dashboard
- Real-time tender statistics
- Advanced filtering and search
- Export to CSV functionality
- Manual scan triggers

### Background Processing
- Scheduled portal scanning (hourly/daily)
- Email notifications for new opportunities
- Database backups and maintenance
- Trend analysis and reporting

## 🛠️ Development

### Local Development Setup
```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py

# Frontend
cd frontend
npm install
npm start
```

### Testing
```bash
# Run all tests
python backend/comprehensive_test.py

# Check dependencies
python backend/check_dependencies.py

# Health check
health-check.bat
```

### Logs and Monitoring
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs backend
docker-compose logs frontend

# Monitor resource usage
docker stats
```

## 🚨 Troubleshooting

### Common Issues

#### Docker Desktop Not Running
```
error during connect: open //./pipe/dockerDesktopLinuxEngine
```
**Solution**: Start Docker Desktop application

#### Services Not Starting
```bash
# Check service status
docker-compose ps

# View logs for failed services
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]
```

#### Database Connection Issues
```bash
# Check database health
docker-compose exec postgres pg_isready -U procurement_user

# Reset database (WARNING: loses data)
docker-compose down -v
docker-compose up -d
```

#### Frontend Not Loading
```bash
# Check if frontend is built
docker-compose exec frontend ls /usr/share/nginx/html

# Rebuild frontend
docker-compose build frontend
docker-compose up -d frontend
```

#### Selenium Grid Issues
```bash
# Check Selenium Grid status
curl http://localhost:4444/wd/hub/status

# Restart Selenium services
docker-compose restart selenium-hub selenium-chrome
```

### Performance Optimization

#### Memory Issues
- Increase Docker Desktop memory allocation (8GB+)
- Reduce concurrent Selenium sessions
- Enable swap space on Linux

#### Slow Scraping
- Adjust timeouts in `selenium_utils.py`
- Reduce scan frequency in `tasks.py`
- Use proxy rotation for high-volume portals

## 📈 Monitoring and Maintenance

### Scheduled Tasks
- **Hourly**: Scan high-priority portals
- **Daily**: Full system scan, database backup
- **Weekly**: Trend analysis, report generation

### Data Management
```bash
# Backup database
docker-compose exec postgres pg_dump -U procurement_user procurement_scanner > backup.sql

# Restore database
docker-compose exec -T postgres psql -U procurement_user procurement_scanner < backup.sql

# Clean old data
docker-compose exec backend python -c "from tasks import clean_expired_tenders; clean_expired_tenders()"
```

## 🔒 Security

### Production Deployment
- Change default passwords in `.env`
- Use HTTPS with proper certificates
- Implement rate limiting
- Set up firewall rules
- Regular security updates

### Data Privacy
- Tender data is public information
- No personal data collection
- GDPR compliant data handling
- Secure API authentication

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs with `docker-compose logs`
3. Run health check: `health-check.bat`
4. Create an issue with detailed error information

---

**Last Updated**: December 2024
**Version**: 1.0.0