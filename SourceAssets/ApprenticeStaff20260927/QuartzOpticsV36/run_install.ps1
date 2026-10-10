param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$taskProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$taskScript=Join-Path $PSScriptRoot 'install_ue.py'
$taskStamp=[DateTime]::Now.ToString('yyyyMMdd-HHmmss')
if(Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
    & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $taskScript `
        -OutputFile (Join-Path $PSScriptRoot "install-$taskStamp-bridge.txt") -MaxOutputChars 2200 -QueueWaitSeconds 60
    if($LASTEXITCODE -ne 0){throw "Quartz V36 bridge failed ($LASTEXITCODE)."}
    exit 0
}
$taskDeadline=[DateTime]::UtcNow.AddMinutes(10)
$taskNotified=$false
while(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^(UnrealBuildTool|cl|link|UnrealEditor-Cmd)\.exe$' -or
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
}) {
    if(-not $taskNotified){Write-Output 'Waiting for the active build or asset commandlet.';$taskNotified=$true}
    if([DateTime]::UtcNow -gt $taskDeadline){Write-Output 'Install has not started; background asset window remains occupied.';exit 75}
    Start-Sleep -Seconds 10
}
if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'An editor opened while waiting; use its existing mutex bridge.'}
& "$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "$taskProject/FPSGAME.uproject" `
    -run=pythonscript "-script=$taskScript" -AllowCommandletRendering -d3d12 `
    -unattended -nop4 -nosplash -nosound -RenderOffscreen `
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' `
    "-abslog=$PSScriptRoot/install-$taskStamp-commandlet.log" *> "$PSScriptRoot/install-$taskStamp-console.log"
if($LASTEXITCODE -ne 0){throw "Quartz V36 commandlet failed ($LASTEXITCODE). See its install log."}
Write-Output 'STAFF_QUARTZ_V36_ASSET_COMMANDLET_FINISHED'
