@echo off
setlocal EnableExtensions
rem Fennec rebrand migration launcher.
rem
rem COPY THIS FILE OUTSIDE THE SUITE BEFORE RUNNING IT (for example to a drive
rem root or %USERPROFILE%). cmd.exe keeps a handle on the running .bat, and
rem Windows refuses to rename a directory while a file inside it is held open -
rem a launcher left inside the suite would block the very rename it performs.
rem
rem The suite is found from FENNEC_SUITE, or by probing each drive for a
rem Fennec-Suite / Colibri-Suite checkout. Nothing assumes a D: drive.
rem
rem Close Qoder and every JetBrains IDE first. Double-click runs a dry run;
rem pass --apply from a terminal to perform the migration.

set "RUN=%TEMP%\fennec-migrate"
if not exist "%RUN%" mkdir "%RUN%"

set "SCRIPT="
if defined FENNEC_SUITE call :probe "%FENNEC_SUITE%"
for %%L in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
  if not defined SCRIPT call :probe "%%L:\Fennec-Suite"
  if not defined SCRIPT call :probe "%%L:\Colibri-Suite"
)
if not defined SCRIPT (
  echo Could not find fennec-installer\migrate_rebrand.py on any drive.
  echo Set FENNEC_SUITE to the suite folder, or run:
  echo   python migrate_rebrand.py --suite ^<dir^>
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
if not defined PY if defined FENNEC_HOME if exist "%FENNEC_HOME%\.venv\Scripts\python.exe" set "PY=%FENNEC_HOME%\.venv\Scripts\python.exe"
if not defined PY for %%L in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
  if not defined PY if exist "%%L:\Colibri\.venv\Scripts\python.exe" set "PY=%%L:\Colibri\.venv\Scripts\python.exe"
)
if not defined PY (
  echo No Python found on PATH, in FENNEC_HOME, or in any drive's Colibri\.venv.
  exit /b 1
)

echo Using %PY%
"%PY%" "%RUN%\migrate_rebrand.py" %*
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo Migration stopped with code %RC%. Close the locking app and re-run.
pause
exit /b %RC%

:probe
if defined SCRIPT goto :eof
if exist "%~1\fennec-installer\migrate_rebrand.py" set "SCRIPT=%~1\fennec-installer\migrate_rebrand.py"
goto :eof
