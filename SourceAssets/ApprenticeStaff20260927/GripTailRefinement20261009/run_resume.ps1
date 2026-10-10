param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$taskProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$taskScript=Join-Path $PSScriptRoot 'resume_meshes.py'
$taskStamp=[DateTime]::Now.ToString('yyyyMMdd-HHmmss')
if(Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
    & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $taskScript `
        -OutputFile (Join-Path $PSScriptRoot "install-$taskStamp-bridge.txt") -MaxOutputChars 2200 -QueueWaitSeconds 60 -RequestTimeoutSeconds 240
    if($LASTEXITCODE -ne 0){throw "Grip/tail bridge failed ($LASTEXITCODE)."}
    exit 0
}
$taskWaitUntil = [DateTime]::UtcNow.AddSeconds(60)
while(Get-Process UnrealEditor-Cmd -ErrorAction SilentlyContinue) {
    if([DateTime]::UtcNow -ge $taskWaitUntil){throw 'An asset commandlet is still running; no grip/tail import started.'}
    Start-Sleep -Seconds 2
}
if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'The editor started during the queue wait; rerun through its bridge.'}
& "$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "$taskProject/FPSGAME.uproject" `
    -run=pythonscript "-script=$taskScript" -AllowCommandletRendering -d3d12 `
    -unattended -nop4 -nosplash -nosound -RenderOffscreen `
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' `
    "-abslog=$PSScriptRoot/install-$taskStamp-commandlet.log" *> "$PSScriptRoot/install-$taskStamp-console.log"
if($LASTEXITCODE -ne 0){throw "Grip/tail import commandlet failed ($LASTEXITCODE). See its install log."}
Write-Output 'STAFF_GRIP_TAIL_ASSET_COMMANDLET_FINISHED'
