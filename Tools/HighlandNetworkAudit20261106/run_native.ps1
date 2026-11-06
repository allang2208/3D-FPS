param([switch]$SkipBuild)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskRun=Join-Path $PSScriptRoot ('Native/'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force -Path $taskRun | Out-Null
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(10))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch occupied; no build or test started.'}
    $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
    if($taskBusy.Count){throw 'Existing UE/build process preserved; no build or test started.'}
    if(-not $SkipBuild){
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -NoHotReloadFromIDE -MaxParallelActions=2 *> "$taskRun/build.log"
        if($LASTEXITCODE -ne 0){throw "Build failed: $taskRun/build.log"}
    }
    Write-Output "HIGHLAND_NATIVE_START $taskRun"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=RuneSwordAudit -HighlandNetworkOnly "-Output=$taskRun/result.json" "-UserDir=$taskRun/Profile/" -nullrhi -nosound -unattended -NoLiveCoding -AssetGatherAll=false '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' "-abslog=$taskRun/native.log" *> "$taskRun/stdout.log"
    $taskExit=$LASTEXITCODE
    @{run=$taskRun;exit_code=$taskExit;rendered=$false;udp=$false;editor_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/native-receipt.json" -Encoding utf8
    Write-Output "HIGHLAND_NATIVE_DONE exit=$taskExit $taskRun"
    if($taskExit -ne 0){throw "Native audit failed: $taskRun/native.log"}
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
