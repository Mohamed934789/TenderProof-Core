@echo off
setlocal
set "DOCKER_CONTEXT=desktop-linux"
set "TP_DOCKER=C:\Program Files\Docker\Docker\resources\bin\docker.exe"
set "TP_EXIT_CODE=1"
pushd "%~dp0" || goto folder_error
set "TENDERPROOF_DOCKER_API_RUNTIME=%~dp0runtime\docker\api"
if not exist "%TP_DOCKER%" goto docker_missing
"%TP_DOCKER%" info >nul 2>&1
if errorlevel 1 goto engine_stopped
"%TP_DOCKER%" compose -f docker-compose.yml stop
if errorlevel 1 goto stop_error
echo TenderProof stopped. Docker Desktop was left running for other applications.
echo Documents, API secret, runtime, audit and one-attempt lock were preserved.
set "TP_EXIT_CODE=0"
goto finish
:engine_stopped
echo Docker Engine is not running. TenderProof containers cannot serve requests while the engine is stopped.
echo No files or locks were changed.
set "TP_EXIT_CODE=0"
goto finish
:docker_missing
echo [ERROR] Docker CLI was not found at the official Docker Desktop path.
goto failed
:stop_error
echo [ERROR] Could not stop TenderProof. Review the error above.
goto failed
:folder_error
echo [ERROR] Could not open the application folder.
pause
endlocal & exit /b 1
:failed
pause
:finish
popd
endlocal & exit /b %TP_EXIT_CODE%
