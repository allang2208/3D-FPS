param(
    [ValidateSet('prepare','install')][string]$Stage='install',
    [string]$EngineRoot='E:/Program Files (x86)/UE_5.8'
)
$ErrorActionPreference='Stop'
$taskProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$taskScript=Join-Path $PSScriptRoot $(if($Stage -eq 'prepare'){'prepare_inputs.py'}else{'install_ue.py'})
$taskStamp=[DateTime]::Now.ToString('yyyyMMdd-HHmmss')
if(Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
    & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $taskScript `
        -OutputFile (Join-Path $PSScriptRoot "$Stage-$taskStamp-bridge.txt") -MaxOutputChars 2200 -QueueWaitSeconds 600
    if($LASTEXITCODE -ne 0){throw "Quartz $Stage bridge failed ($LASTEXITCODE). Existing editor preserved."}
    exit 0
}
$taskNotified=$false
while(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^(UnrealBuildTool|cl|link|UnrealEditor-Cmd)\.exe$' -or
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
}) {
    if(-not $taskNotified){Write-Output 'Waiting for the current native build or asset commandlet.';$taskNotified=$true}
    Start-Sleep -Seconds 10
}
if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'An editor opened while waiting; use its existing mutex bridge.'}
& "$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "$taskProject/FPSGAME.uproject" `
    -run=pythonscript "-script=$taskScript" -AllowCommandletRendering -d3d12 `
    -unattended -nop4 -nosplash -nosound -RenderOffscreen `
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' `
    "-abslog=$PSScriptRoot/$Stage-$taskStamp-commandlet.log" *> "$PSScriptRoot/$Stage-$taskStamp-console.log"
if($LASTEXITCODE -ne 0){throw "Quartz $Stage commandlet failed ($LASTEXITCODE). See $Stage-$taskStamp-commandlet.log."}
Write-Output "STAFF_QUARTZ_V35_$($Stage.ToUpper())_SAVED"
