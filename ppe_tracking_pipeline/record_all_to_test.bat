@echo off
REM ============================================================
REM  PPE Tracking — BATCH record every clip in a folder
REM
REM  Loops over all videos in  ..\to_test\  (or a folder you
REM  pass / drag in), runs the tracking pipeline on each, and
REM  saves one annotated .mp4 per clip into  recordings\.
REM
REM  USAGE:
REM    1. Double-click            -> processes ..\to_test\
REM    2. Drag a FOLDER onto it   -> processes that folder
REM    3. record_all_to_test.bat C:\ppe\to_test
REM ============================================================
setlocal EnableDelayedExpansion

REM ---- Settings (tune for distance) -------------------------
set DEVICE=cuda
set PPE_IMGSZ=1280
set PPE_CONF=0.20
set TRACKER=bytetrack
set TRACK_BUFFER=60
set DISPLAY_WINDOW=1
REM  DISPLAY_WINDOW=1 shows each clip live (press q to skip to next).
REM  DISPLAY_WINDOW=0 runs unattended/headless (faster for many clips).
REM  Distant PPE missed? raise PPE_IMGSZ to 1536. Occlusion? TRACKER=botsort.
REM -----------------------------------------------------------

REM ---- Resolve the input folder -----------------------------
set "TESTDIR=%~1"
if "%TESTDIR%"=="" set "TESTDIR=%~dp0..\to_test"

if not exist "%TESTDIR%" (
  echo.
  echo [ERROR] Folder not found: "%TESTDIR%"
  echo Copy your clips to  ..\to_test\  or drag a folder onto this .bat
  echo.
  pause
  exit /b 1
)

set "SAVEDIR=%~dp0recordings"
if not exist "%SAVEDIR%" mkdir "%SAVEDIR%"

set "EXTRA="
if "%DISPLAY_WINDOW%"=="0" set "EXTRA=--no-display"

echo.
echo ============================================================
echo  Input folder : %TESTDIR%
echo  Output folder: %SAVEDIR%
echo  Model        : ..\models\best.pt  (4-class)
echo  Device=%DEVICE%  imgsz=%PPE_IMGSZ%  conf=%PPE_CONF%  tracker=%TRACKER%
echo ============================================================
echo.

set /a COUNT=0
pushd "%TESTDIR%"
for %%F in (*.mp4 *.MOV *.mov *.avi *.mkv) do (
    set /a COUNT+=1
    set "OUT=%SAVEDIR%\%%~nF_annotated.mp4"
    echo ------------------------------------------------------------
    echo [!COUNT!] Processing: %%~nxF
    echo        -> !OUT!
    echo ------------------------------------------------------------
    python "%~dp0run.py" ^
        --source "%%~fF" ^
        --device %DEVICE% ^
        --ppe-imgsz %PPE_IMGSZ% ^
        --ppe-conf %PPE_CONF% ^
        --tracker %TRACKER% ^
        --track-buffer %TRACK_BUFFER% ^
        --save "!OUT!" %EXTRA%
    echo.
)
popd

echo ============================================================
echo  Done. Processed !COUNT! clip(s).
echo  Recordings saved in: %SAVEDIR%
echo ============================================================
echo.
pause
