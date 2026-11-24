@echo off
setlocal
cd /d "%~dp0"

rem ---- Python used to create the virtual environment (override with HEBREW_PYTHON) ----
if "%HEBREW_PYTHON%"=="" set "HEBREW_PYTHON=C:\workspace\vms\shared\workspace\common\developement\python\3.14\python.exe"
set "VENV=%~dp0.venv"
set "VPY=%VENV%\Scripts\python.exe"
if "%PORT%"=="" set "PORT=5000"

echo [1/5] Checking Python...
if not exist "%HEBREW_PYTHON%" (
    echo ERROR: Python not found at %HEBREW_PYTHON%
    echo Set HEBREW_PYTHON to your python.exe and try again.
    goto :fail
)
"%HEBREW_PYTHON%" --version || goto :fail

echo [2/5] Checking virtual environment...
if not exist "%VPY%" (
    echo Creating virtual environment in .venv ...
    "%HEBREW_PYTHON%" -m venv "%VENV%" || goto :fail
)

echo [3/5] Checking dependencies...
"%VPY%" -c "import flask, edge_tts, truststore, numpy, soundfile, torch, transformers" 2>nul
if errorlevel 1 (
    echo Installing dependencies from requirements.txt ^(first time: ~300 MB, a few minutes^)...
    "%VPY%" -m pip install --disable-pip-version-check -q -r requirements.txt || goto :fail
    "%VPY%" -c "import flask, edge_tts, truststore, numpy, soundfile, torch, transformers" || goto :fail
)
echo Dependencies OK.

echo [4/5] Checking audio clips...
"%VPY%" generate_audio.py
if errorlevel 1 (
    echo WARNING: some clips could not be generated ^(no internet?^).
    echo          The browser's built-in Hebrew voice will be used for those.
)

echo [5/5] Checking speech model for the quiz...
"%VPY%" -c "import truststore; truststore.inject_into_ssl(); import speech_match; speech_match.ensure_model()" 2>nul
if errorlevel 1 (
    echo Downloading speech model ^(first time only, ~1.2 GB^)...
    "%VPY%" -c "import truststore; truststore.inject_into_ssl(); import speech_match; speech_match.ensure_model()"
    if errorlevel 1 echo WARNING: speech model not available - the quiz will not work until it is downloaded.
)

echo.
echo Starting app at http://127.0.0.1:%PORT%  ^(Ctrl+C to stop^)
start "" "http://127.0.0.1:%PORT%"
"%VPY%" app.py
goto :eof

:fail
echo.
echo Setup failed.
pause
exit /b 1
