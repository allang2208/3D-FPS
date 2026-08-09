# 5080 远程启动 ComfyUI（通过 schtasks 计划任务运行，防 SSH 断连杀进程）
$python = 'D:\开发文件\ComfyUI\.venv\Scripts\python.exe'
$args = @('main.py','--listen','0.0.0.0','--port','8188','--enable-cors-header','*')
Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory 'D:\开发文件\ComfyUI' -WindowStyle Hidden
Start-Sleep -Seconds 2
Write-Output 'ComfyUI starting...'
