@echo off
echo ========================================
echo Canadian Procurement Scanner Setup
echo ========================================
echo.

echo [1/6] Checking Docker Desktop...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Desktop is not running!
    echo Please start Docker Desktop and run this script again.
    pause
    exit /b 1
)
echo ✅ Docker Desktop is running

echo.
echo [2/6] Creating environment file...
if not exist .env (
    copy env.example .env
    echo ✅ Created .env file from template
) else (
    echo ✅ .env file already exists
)

echo.
echo [3/6] Creating necessary directories...
if not exist data mkdir data
if not exist data\downloads mkdir data\downloads
if not exist data\tenders mkdir data\tenders
if not exist data\backups mkdir data\backups
if not exist logs mkdir logs
echo ✅ Directories created

echo.
echo [4/6] Building Docker images...
docker-compose build --no-cache
if %errorlevel% neq 0 (
    echo ❌ Docker build failed!
    pause
    exit /b 1
)
echo ✅ Docker images built successfully

echo.
echo [5/6] Starting services...
docker-compose up -d
if %errorlevel% neq 0 (
    echo ❌ Failed to start services!
    pause
    exit /b 1
)
echo ✅ Services started successfully

echo.
echo [6/6] Waiting for services to be ready...
timeout /t 30 /nobreak >nul

echo.
echo ========================================
echo 🎉 Setup Complete!
echo ========================================
echo.
echo Service Status:
docker-compose ps
echo.
echo Access Points:
echo - Frontend: http://localhost:3000
echo - API: http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo - Database: localhost:5432
echo - Redis: localhost:6379
echo.
echo To view logs: docker-compose logs -f
echo To stop services: docker-compose down
echo ========================================
pause 