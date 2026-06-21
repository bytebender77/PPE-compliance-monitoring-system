@echo off
REM ============================================================
REM  PPE Tracking — Record annotated CCTV CLIP (Windows + GPU)
REM
REM  Runs the tracking pipeline on a recorded video, shows the
REM  live window with PPE-violation marking, and SAVES an
REM  annotated .mp4 you can show.
REM
REM  USAGE (any of these):
REM    1. Double-click this file          -> uses far.MOV by default
REM    2. Drag a video file ONTO this .bat -> processes that clip
REM    3. record_cctv_clip.bat C:\path\to\clip.mp4
REM ============================================================
setlocal

REM ---- Settings you may tune for distance -------------------
set DEVICE=cuda
set PPE_IMGSZ=1280
set PPE_CONF=0.20
set TRACKER=bytetrack
set TRACK_BUFFER=60
REM  Catch more DISTANT PPE? raise PPE_IMGSZ to 1536 (slower).
REM  Crossing / occluded workers? set TRACKER=botsort.
REM -----------------------------------------------------------

REM ---- Resolve the clip -------------------------------------
set "CLIP=%~1"
if "%CLIP%"=="" set "CLIP=%~dp0..\datasets\new\far.MOV"

if not exist "%CLIP%" (
  echo.
  echo [ERROR] Clip not found: "%CLIP%"
  echo Copy your CCTV clips to  ..\datasets\new\  or drag a file onto this .bat
  echo.
  pause
  exit /b 1
)

REM ---- Build a timestamped output path ----------------------
if not exist "%~dp0recordings" mkdir "%~dp0recordings"
for %%F in ("%CLIP%") do set "CLIPNAME=%%~nF"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%I"
set "OUT=%~dp0recordings\%CLIPNAME%_annotated_%STAMP%.mp4"

echo.
echo ============================================================
echo  Clip   : %CLIP%
echo  Output : %OUT%
echo  Model  : ..\models\best.pt  (4-class)
echo  Device : %DEVICE%   imgsz=%PPE_IMGSZ%  conf=%PPE_CONF%
echo  Tracker: %TRACKER%  buffer=%TRACK_BUFFER%
echo ============================================================
echo  A window opens. Press  q  or  Esc  to stop early.
echo  Recording is written even if you quit early.
echo.

python "%~dp0run.py" ^
    --source "%CLIP%" ^
    --device %DEVICE% ^
    --ppe-imgsz %PPE_IMGSZ% ^
    --ppe-conf %PPE_CONF% ^
    --tracker %TRACKER% ^
    --track-buffer %TRACK_BUFFER% ^
    --save "%OUT%"

echo.
echo Done. Saved recording:
echo   %OUT%
echo.
pause
