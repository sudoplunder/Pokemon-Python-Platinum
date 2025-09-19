@echo off
echo Game - Setup and Launch
echo.
echo Checking and installing requirements...
python setup_requirements.py
if %errorlevel% neq 0 (
    echo.
    echo Requirements setup failed! Please check the errors above.
    pause
    exit /b 1
)
echo.
echo Verifying all dependencies work correctly...
python verify_dependencies.py
if %errorlevel% neq 0 (
    echo.
    echo Dependency verification failed! Some packages may not work properly.
    echo You can still try to run the game, but it may have issues.
    echo.
    choice /C YN /M "Do you want to continue anyway"
    if errorlevel 2 (
        echo Setup cancelled.
        pause
        exit /b 1
    )
)
echo.
echo All systems ready! Starting game...
python main.py
pause