param([string]$ComfyRoot='D:\开发文件\ComfyUI')
$ErrorActionPreference='Stop'
# Activation only: no test prompt, model load or output rendering.
$queue=Invoke-RestMethod 'http://127.0.0.1:8188/queue'
if($queue.queue_running.Count -gt 0 -or $queue.queue_pending.Count -gt 0){
    throw 'ComfyUI has queued work; restart deferred to preserve it.'
}
$workflowRoot=Join-Path $ComfyRoot 'user\default\workflows\Mechanical3D'
New-Item -ItemType Directory -Path $workflowRoot -Force | Out-Null
Copy-Item -Path 'D:\Mechanical3DSetup\workflows\*.json' -Destination $workflowRoot -Force
$listeners=Get-NetTCPConnection -LocalPort 8188 -State Listen
foreach($processId in ($listeners.OwningProcess | Sort-Object -Unique)){
    $process=Get-CimInstance Win32_Process -Filter "ProcessId=$processId"
    if($process.Name -ne 'python.exe' -or $process.CommandLine -notlike '*main.py*--port 8188*'){
        throw 'Port belongs to an unexpected process; not stopping it.'
    }
    Stop-Process -Id $processId -Force
}
$python=Join-Path $ComfyRoot '.venv\Scripts\python.exe'
$startup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$started=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine=('"'+$python+'" "D:\Mechanical3DSetup\launch_comfy.py" "'+$ComfyRoot+'"')
    CurrentDirectory=$ComfyRoot
    ProcessStartupInformation=$startup
}
if($started.ReturnValue -ne 0){throw "ComfyUI launch failed: $($started.ReturnValue)"}
Write-Output "ComfyUI launch requested through WMI; no generation or tests run."

