@echo off
echo 🚀 BackupDocu lokale Tests starten...
echo.

cd /d "%~dp0"

echo 📦 Installiere Dependencies...
pip install -r requirements.txt
pip install requests
if %errorlevel% neq 0 (
    echo ❌ Fehler bei Dependency-Installation
    pause
    exit /b 1
)

echo.
echo 🧪 Führe Tests aus...
python test_local.py
if %errorlevel% neq 0 (
    echo.
    echo ❌ Tests fehlgeschlagen!
    pause
    exit /b 1
)

echo.
echo ✅ Alle Tests erfolgreich!
echo.
echo 💡 Jetzt kannst du die App starten mit:
echo    docker-compose up --build
echo oder
echo    uvicorn backend.main:app --reload
pause