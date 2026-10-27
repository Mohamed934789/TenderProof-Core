@echo off
setlocal
set "DOCKER_CONTEXT=desktop-linux"
set "TP_DOCKER=C:\Program Files\Docker\Docker\resources\bin\docker.exe"
set "TENDERPROOF_DOCKER_DESKTOP=C:\Program Files\Docker\Docker\Docker Desktop.exe"
set "TP_EXIT_CODE=1"
pushd "%~dp0" || goto folder_error
rem Always reuse this persistent runtime. Never reset a consumed AI attempt.
set "TENDERPROOF_DOCKER_API_RUNTIME=%~dp0runtime\docker\api"
if not exist "%TP_DOCKER%" goto docker_missing
if not exist "docker-compose.yml" goto config_missing
if not exist "docker-compose.ai.yml" goto config_missing
set "TP_REAL_AI=0"
set "TP_AI_COMPOSE="
if /i "%~1"=="--real-ai" goto real_ai_setup
goto launch_mode_ready
:real_ai_setup
set "TP_REAL_AI=1"
set "TP_AI_COMPOSE=-f docker-compose.ai.yml"
if not exist ".secrets\openai_api_key" goto secret_missing
for %%F in (".secrets\openai_api_key") do if %%~zF EQU 0 goto secret_missing
:launch_mode_ready
"%TP_DOCKER%" info >nul 2>&1
if not errorlevel 1 goto engine_ready
if not exist "%TENDERPROOF_DOCKER_DESKTOP%" goto desktop_missing
echo Starting Docker Desktop. Please wait...
powershell.exe -NoProfile -Command "Start-Process -FilePath $env:TENDERPROOF_DOCKER_DESKTOP -WindowStyle Hidden"
if errorlevel 1 goto desktop_error
set /a TP_WAIT=0 >nul
:wait_engine
"%TP_DOCKER%" info >nul 2>&1
if not errorlevel 1 goto engine_ready
if %TP_WAIT% GEQ 120 goto engine_error
powershell.exe -NoProfile -Command "Start-Sleep -Seconds 2"
set /a TP_WAIT+=2 >nul
goto wait_engine
:engine_ready
echo Starting TenderProof. No AI analysis is started by this launcher.
"%TP_DOCKER%" compose -f docker-compose.yml %TP_AI_COMPOSE% up --build -d --wait --wait-timeout 120
if errorlevel 1 goto compose_error
powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop'; try { $h=Invoke-RestMethod -Uri 'http://127.0.0.1:8002/health' -TimeoutSec 10; if ($h.status -ne 'ok') { throw 'API health check failed' }; $u=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8503/_stcore/health' -TimeoutSec 10; if ($u.StatusCode -ne 200) { throw 'UI health check failed' }; if ($env:TP_REAL_AI -ne '1') { if ($h.paid_ai_enabled) { throw 'Unexpected AI activation in Saved Demo mode' }; Write-Host '[READY] Saved Demo ready. Paid AI is disabled. No API key required.'; exit 0 }; if ($h.ai_readiness.code -eq 'ATTEMPT_USED') { Write-Host '[LOCKED] The authorized AI attempt was already used. Lock and audit preserved. Saved Demo is still available.'; exit 3 }; if (-not $h.paid_ai_enabled -or $h.ai_readiness.code -ne 'READY') { Write-Host ('[NOT READY] ' + $h.ai_readiness.message); exit 1 }; Write-Host '[READY] Real AI settings ready. No OpenAI request was sent. Key validity and credit are not verified.'; Write-Host 'Choose AI in Advanced Settings, upload PDFs and confirm cost before pressing Start. One attempt only.'; exit 0 } catch { Write-Host ('[ERROR] ' + $_.Exception.Message); exit 1 }"
if errorlevel 4 goto readiness_error
if errorlevel 3 goto attempt_used
if errorlevel 1 goto readiness_error
start "" "http://127.0.0.1:8503"
set "TP_EXIT_CODE=0"
goto finish
:attempt_used
start "" "http://127.0.0.1:8503"
set "TP_EXIT_CODE=3"
goto failed
:docker_missing
echo [ERROR] Docker CLI was not found at the official Docker Desktop path.
echo Install Docker Desktop for Windows. Do not select a program to open an extensionless docker file.
goto failed
:config_missing
echo [ERROR] Docker Compose files are missing next to this launcher.
goto failed
:secret_missing
echo [ERROR] .secrets\openai_api_key is missing or empty. Add the key in a local editor as described in README.md.
echo Never paste the key into this launcher, the terminal, or Dockerfile.
goto failed
:desktop_missing
echo [ERROR] Docker Desktop executable was not found.
goto failed
:desktop_error
echo [ERROR] Could not start Docker Desktop. Open it manually and review its error.
goto failed
:engine_error
echo [ERROR] Docker Engine did not become ready within 120 seconds. Check Docker Desktop, WSL2 and Linux containers mode.
goto failed
:compose_error
echo [ERROR] Containers could not start. Review the Docker error above. No AI analysis was requested.
goto failed
:readiness_error
echo [ERROR] Application is not ready for Real AI. Resolve the message above. No AI analysis was requested.
goto failed
:folder_error
echo [ERROR] Could not open the application folder.
pause
endlocal & exit /b 1
:failed
echo No lock, audit, or document was removed. No paid attempt was rearmed.
pause
:finish
popd
endlocal & exit /b %TP_EXIT_CODE%
