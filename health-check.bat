@echo off
echo ========================================
echo Health Check - Canadian Procurement Scanner
echo ========================================
echo.

echo [1/7] Checking Docker Desktop...
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Docker Desktop is running
) else (
    echo ❌ Docker Desktop is not running
    goto :end
)

echo.
echo [2/7] Checking Docker Compose services...
docker-compose ps
if %errorlevel% neq 0 (
    echo ❌ Docker Compose services not running
    goto :end
)

echo.
echo [3/7] Testing database connection...
docker-compose exec -T postgres pg_isready -U procurement_user -d procurement_scanner
if %errorlevel% equ 0 (
    echo ✅ Database is healthy
) else (
    echo ❌ Database connection failed
)

echo.
echo [4/7] Testing Redis connection...
docker-compose exec -T redis redis-cli ping
if %errorlevel% equ 0 (
    echo ✅ Redis is healthy
) else (
    echo ❌ Redis connection failed
)

echo.
echo [5/7] Testing Selenium Grid...
curl -s http://localhost:4444/wd/hub/status >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Selenium Grid is healthy
) else (
    echo ❌ Selenium Grid is not responding
)

echo.
echo [6/7] Testing Backend API...
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Backend API is healthy
) else (
    echo ❌ Backend API is not responding
)

echo.
echo [7/7] Testing Frontend...
curl -s http://localhost:3000 >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Frontend is healthy
) else (
    echo ❌ Frontend is not responding
)

echo.
echo ========================================
echo Health Check Complete
echo ========================================
echo.
echo To view detailed logs:
echo - Backend: docker-compose logs backend
echo - Frontend: docker-compose logs frontend
echo - Database: docker-compose logs postgres
echo - All services: docker-compose logs -f
echo.

:end
pause 