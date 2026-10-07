param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$taskProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskScript=Join-Path $PSScriptRoot 'install_current_ue.py'
$taskStamp=[DateTime]::Now.ToString('yyyyMMdd-HHmmss')
function Invoke-ExistingBridge {
    & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $taskScript `
        -OutputFile (Join-Path $PSScriptRoot "install-$taskStamp-bridge.txt") -MaxOutputChars 2200 -QueueWaitSeconds 600
    if($LASTEXITCODE -ne 0){throw 'Azure Dragon V10 restore failed; existing editor preserved.'}
}
if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){Invoke-ExistingBridge;exit 0}
$taskNotified=$false
while(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^(UnrealBuildTool|cl|link|UnrealEditor-Cmd)\.exe$' -or
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
}){
    if(-not $taskNotified){Write-Output 'Waiting for current native build or asset commandlet.';$taskNotified=$true}
    Start-Sleep -Seconds 10
}
if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){Invoke-ExistingBridge;exit 0}
& "$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "$taskProject/FPSGAME.uproject" `
    -run=pythonscript "-script=$taskScript" -AllowCommandletRendering -d3d12 `
    -unattended -nop4 -nosplash -nosound -RenderOffscreen `
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' `
    "-abslog=$PSScriptRoot/install-$taskStamp-commandlet.log" *> "$PSScriptRoot/install-$taskStamp-console.log"
if($LASTEXITCODE -ne 0){throw "Azure Dragon V10 restore failed; see install-$taskStamp-commandlet.log."}
Write-Output 'AZURE_DRAGON_V10_RESTORED'
