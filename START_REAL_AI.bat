@echo off
rem Explicit opt-in only. Requires a local secret; never starts analysis automatically.
call "%~dp0START_TENDERPROOF.bat" --real-ai
exit /b %errorlevel%
