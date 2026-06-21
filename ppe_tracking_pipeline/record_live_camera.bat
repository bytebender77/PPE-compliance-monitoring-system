@echo off
REM ============================================================
REM  PPE Tracking — Record LIVE camera (Windows + GPU)
REM
REM  Runs the tracking pipeline on a live webcam or RTSP CCTV
REM  feed, shows the window with PPE-violation marking, and
REM  SAVES an annotated .mp4 you can show.
REM
REM  USAGE:
REM    Webcam (default index 0):   record_live_camera.bat
REM    Other webcam:               record_live_camera.bat 1
REM    RTSP CCTV camera:           record_live_camera.bat "rtsp://user:pass@192.168.1.50:554/stream1"
REM ============================================================
setlocal

REM ---- Settings ---------------------------------------------
set DEVICE=cuda
set PPE_IMGSZ=1280
set PPE_CONF=0.20
set TRACKER=bytetrack
set TRACK_BUFFER=60
REM -----------------------------------------------------------

REM ---- Resolve the source (webcam index or RTSP url) --------
set "SRC=%~1"
if "%SRC%"=="" set "SRC=0"

REM ---- Build a timestamped output path ----------------------
if not exist "%~dp0recordings" mkdir "%~dp0recordings"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%I"
set "OUT=%~dp0recordings\live_annotated_%STAMP%.mp4"

echo.
echo ============================================================
echo  Source : %SRC%
echo  Output : %OUT%
echo  Device : %DEVICE%   imgsz=%PPE_IMGSZ%  conf=%PPE_CONF%
echo  Tracker: %TRACKER%  buffer=%TRACK_BUFFER%
echo ============================================================
echo  A window opens. Press  q  or  Esc  to stop and finish.
echo  Live-tune keys:  [ ]  =N    - =  =K    , .  =presence
echo.

python "%~dp0run.py" ^
    --source "%SRC%" ^
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
