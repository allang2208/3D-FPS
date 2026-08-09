@echo off
chcp 65001 >nul
schtasks /create /tn ComfyUI_RESTART_3D /tr "C:\Users\WINDOWS\AppData\Local\Programs\Python\Python311\python.exe D:\launch_comfyui_5080.py" /sc once /st 00:00 /f
schtasks /run /tn ComfyUI_RESTART_3D
echo Restart task launched.
