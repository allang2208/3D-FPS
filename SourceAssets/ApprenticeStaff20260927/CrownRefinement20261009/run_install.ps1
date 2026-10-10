param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$taskProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$taskScript=Join-Path $PSScriptRoot 'install_ue.py'
$taskStamp=[DateTime]::Now.ToString('yyyyMMdd-HHmmss')
if(Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
    & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $taskScript `
        -OutputFile (Join-Path $PSScriptRoot "install-$taskStamp-bridge.txt") -MaxOutputChars 2200 -QueueWaitSeconds 60 -RequestTimeoutSeconds 240
    if($LASTEXITCODE -ne 0){throw "Crown bridge failed ($LASTEXITCODE)."}
    exit 0
}
if(Get-Process UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An asset commandlet is running; no crown import started.'}
& "$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "$taskProject/FPSGAME.uproject" `
    -run=pythonscript "-script=$taskScript" -AllowCommandletRendering -d3d12 `
    -unattended -nop4 -nosplash -nosound -RenderOffscreen `
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' `
    "-abslog=$PSScriptRoot/install-$taskStamp-commandlet.log" *> "$PSScriptRoot/install-$taskStamp-console.log"
if($LASTEXITCODE -ne 0){throw "Crown import commandlet failed ($LASTEXITCODE). See its install log."}
Write-Output 'STAFF_CROWN_ASSET_COMMANDLET_FINISHED'
