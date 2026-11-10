@echo off
setlocal EnableExtensions
rem Fennec rebrand migration launcher.
rem
rem COPY THIS FILE OUTSIDE THE SUITE BEFORE RUNNING IT (e.g. to D:\).
rem cmd.exe keeps a handle on the running .bat, and Windows refuses to rename a
rem directory while a file inside it is held open - a launcher left in
rem D:\Colibri-Suite would block the very rename it performs.
rem
rem Close Qoder and every JetBrains IDE first. Double-click runs a dry run;
rem pass --apply from a terminal to perform the migration.

set "RUN=%TEMP%\fennec-migrate"
if not exist "%RUN%" mkdir "%RUN%"

set "SCRIPT="
for %%D in ("D:\Fennec-Suite" "D:\Colibri-Suite") do (
  if exist "%%~D\fennec-installer\migrate_rebrand.py" set "SCRIPT=%%~D\fennec-installer\migrate_rebrand.py"
)
if not defined SCRIPT (
  echo Could not find fennec-installer\migrate_rebrand.py under D:\Fennec-Suite or D:\Colibri-Suite.
  echo Pass the suite location: migrate_rebrand.py --suite ^<dir^>
  exit /b 1
)

rem Run a copy from TEMP so the interpreter never holds the suite open either.
copy /y "%SCRIPT%" "%RUN%\migrate_rebrand.py" >nul
cd /d "%TEMP%"

set "PY="
for %%P in (python.exe py.exe) do (
  if not defined PY (
    where %%P >nul 2>nul && set "PY=%%P"
  )
)
if not defined PY (
  if exist "D:\Colibri\.venv\Scripts\python.exe" set "PY=D:\Colibri\.venv\Scripts\python.exe"
)
if not defined PY (
  echo No Python found on PATH and no engine venv at D:\Colibri\.venv.
  exit /b 1
)

echo Using %PY%
"%PY%" "%RUN%\migrate_rebrand.py" %*
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo Migration stopped with code %RC%. Close the locking app and re-run.
pause
exit /b %RC%