@echo off
chcp 65001 >nul
for /d %%D in ("D:\*") do if exist "%%D\ComfyUI\main.py" set CFU=%%D\ComfyUI
if not defined CFU (
  echo ComfyUI not found
  exit /b 1
)
start "ComfyUI-5080" /min cmd /c "cd /d %CFU% && %CFU%\.venv\Scripts\python.exe main.py --listen 0.0.0.0 --port 8188 --enable-cors-header * > D:\comfyui_3d.log 2>&1"
echo started
