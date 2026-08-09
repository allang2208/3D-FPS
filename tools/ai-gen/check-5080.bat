@echo off
chcp 65001 >nul
echo === python processes === > D:\check5080.txt
tasklist /FI "IMAGENAME eq python.exe" >> D:\check5080.txt
echo === port 8188 === >> D:\check5080.txt
netstat -ano | findstr :8188 >> D:\check5080.txt
echo === log tail === >> D:\check5080.txt
powershell -NoProfile -Command "Get-Content 'D:\开发文件\ComfyUI\user\comfyui_8188.log' -Tail 15" >> D:\check5080.txt
