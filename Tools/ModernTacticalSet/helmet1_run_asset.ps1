# Task-local copy of run_asset.ps1: bypass stalled registry cache reads for this helmet import.
param([string]$Script='helmet1_save.py',[string]$ReceiptName=('tactical-'+(Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference='Stop'
$tacticalProject='D:/FPS3D/FPSGAME'
if($Script -eq 'grant.py'){
    & (Join-Path $tacticalProject 'Tools/ModernTacticalSet/grant_inventory.ps1')
    exit $LASTEXITCODE
}
$tacticalLogs=Join-Path $tacticalProject 'SourceAssets/ModernTacticalSet20261113/Integration/Logs'
[void](New-Item -ItemType Directory -Force -Path $tacticalLogs)
$tacticalScript=Join-Path $tacticalProject ('Tools/ModernTacticalSet/'+$Script)
$tacticalOutput=Join-Path $tacticalLogs ($ReceiptName+'.txt')
if(Test-Path -LiteralPath $tacticalOutput){throw 'Use a fresh tactical receipt name.'}
function Test-TacticalProjectOwner($tacticalProcess){
    foreach($tacticalMatch in [regex]::Matches($tacticalProcess.CommandLine,'"([^"]+\.uproject)"|(\S+\.uproject)')){
        $tacticalPath=if($tacticalMatch.Groups[1].Success){$tacticalMatch.Groups[1].Value}else{$tacticalMatch.Groups[2].Value}
        if($tacticalPath.Replace('\','/') -eq "$tacticalProject/FPSGAME.uproject"){return $true}
    }
    $tacticalModule=@((Get-Process -Id $tacticalProcess.ProcessId -ErrorAction SilentlyContinue).Modules | Where-Object {$_.ModuleName -eq 'UnrealEditor-FPSGAME.dll'})
    return [bool]@($tacticalModule | Where-Object {$_.FileName.Replace('\','/') -eq "$tacticalProject/Binaries/Win64/UnrealEditor-FPSGAME.dll"}).Count
}
$tacticalProcesses=@(Get-CimInstance Win32_Process)
$tacticalEditor=@($tacticalProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)' -and (Test-TacticalProjectOwner $_)})
if($tacticalEditor.Count){
    $tacticalGuard=Join-Path $tacticalLogs ($ReceiptName+'-entry.py')
    $tacticalPythonPath=ConvertTo-Json -InputObject $tacticalScript -Compress
    @"
import runpy
import unreal as u
editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor and editor.is_in_play_in_editor():
    print('TS01_DEFERRED_PLAY')
else:
    runpy.run_path($tacticalPythonPath,run_name='__main__')
"@ | Set-Content -LiteralPath $tacticalGuard -Encoding utf8
    $tacticalAttempt=0
    while($tacticalEditor.Count){
        & (Join-Path $tacticalProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $tacticalGuard -OutputFile $tacticalOutput -MaxOutputChars 2500 -QueueWaitSeconds 3600 -RequestTimeoutSeconds 1800
        if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
        if(-not(Select-String -LiteralPath $tacticalOutput -SimpleMatch 'TS01_DEFERRED_PLAY' -Quiet)){exit 0}
        Start-Sleep -Seconds 45
        $tacticalAttempt++
        $tacticalOutput=Join-Path $tacticalLogs ($ReceiptName+'-resume-'+$tacticalAttempt+'.txt')
        $tacticalEditor=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)' -and (Test-TacticalProjectOwner $_)})
    }
}
$tacticalGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$tacticalHeld=$false
try{
    Write-Output 'Queued for shared asset batch.'
    try{$tacticalHeld=$tacticalGate.WaitOne()}catch [Threading.AbandonedMutexException]{$tacticalHeld=$true}
    while($true){
        $tacticalBusy=@(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -eq 'UnrealEditor.exe' -and (Test-TacticalProjectOwner $_)) -or
            ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -like '*ModernTacticalSet20261113*AssetHost*')
        })
        if(-not $tacticalBusy.Count){break}
        if(@($tacticalBusy | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)'}).Count){throw 'The project editor appeared; retain it and use the bridge on the next batch.'}
        Write-Output 'Waiting for the project engine/build owner.'
        try{Wait-Process -Id $tacticalBusy[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $tacticalBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    $tacticalLog=Join-Path $tacticalLogs ($ReceiptName+'.log')
    # This engine-only host mounts only the task-owned helmet package directory.
    # It does not hold the main project's game DLL open during unrelated builds.
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$tacticalProject/SourceAssets/ModernTacticalSet20261113/HelmetDetailR1/AssetHost/HelmetAssetHost.uproject" '/Engine/Maps/Entry' '-run=pythonscript' "-script=$tacticalScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' '-Multiprocess' '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' '-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen' '-NoAssetRegistryCache' '-AssetGatherAll=false' '-asyncskinnedassetcompilation=0' '-asyncstaticmeshcompilation=0' '-asynctexturecompilation=0' '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh' '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$tacticalLog" *> $tacticalOutput
    $tacticalExit=$LASTEXITCODE;Write-Output "Tactical commandlet exit=$tacticalExit; log=$tacticalLog";Get-Content -LiteralPath $tacticalOutput -Tail 3;exit $tacticalExit
}finally{if($tacticalHeld){$tacticalGate.ReleaseMutex()};$tacticalGate.Dispose()}
