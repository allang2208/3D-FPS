param([ValidateSet('Build','Assets','All')][string]$Stage='All')
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskEngine='E:/Program Files (x86)/UE_5.8'
$taskRoot=$PSScriptRoot
$taskReceiptPath=Join-Path $taskRoot 'delivery.json'
$taskStamp=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')
$taskReceipt=[ordered]@{stage=$Stage;state='waiting';runtime_tested=$false;source_pose_rendered=$false;targets=@{};logs=@{}}
if($Stage -eq 'Assets' -and (Test-Path -LiteralPath $taskReceiptPath)){
    $taskPrevious=Get-Content -LiteralPath $taskReceiptPath -Raw|ConvertFrom-Json
    foreach($taskProperty in $taskPrevious.targets.PSObject.Properties){$taskReceipt.targets[$taskProperty.Name]=$taskProperty.Value}
    foreach($taskProperty in $taskPrevious.logs.PSObject.Properties){$taskReceipt.logs[$taskProperty.Name]=$taskProperty.Value}
}
function Write-Receipt { [IO.File]::WriteAllText($taskReceiptPath,($taskReceipt|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false)) }
function Wait-Window {
    $taskDeadline=[DateTime]::UtcNow.AddMinutes(40)
    while($true){
        $taskProcesses=@(Get-CimInstance Win32_Process)
        $taskGUI=@($taskProcesses|Where-Object {$_.Name -eq 'UnrealEditor.exe' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME\.uproject')})
        if($taskGUI.Count){throw 'The FPSGAME editor is running. Its loaded/unsaved assets are preserved; close it before this production stage.'}
        $taskBusy=@($taskProcesses|Where-Object {$_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe','UnrealEditor-Cmd.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if(!$taskBusy.Count){return}
        if([DateTime]::UtcNow -gt $taskDeadline){throw 'The existing build window did not release. No process was stopped.'}
        Start-Sleep -Seconds 5
    }
}
function Build-Target([string]$Target){
    $taskReceipt.state='waiting_for_'+$Target;Write-Receipt;Wait-Window
    $taskReceipt.state='building_'+$Target;Write-Receipt
    $taskLog=Join-Path $taskRoot ('build-'+$Target+'-'+$taskStamp+'.log')
    $taskReceipt.logs[$Target]=$taskLog;Write-Receipt
    & (Join-Path $taskEngine 'Engine/Build/BatchFiles/Build.bat') $Target Win64 Development "-Project=$taskProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE "-Log=$taskLog"
    if($LASTEXITCODE -ne 0){throw "$Target build failed: $LASTEXITCODE"}
    $taskReceipt.targets[$Target]='Succeeded';Write-Receipt
}
function Produce-Assets([string]$Script,[string]$Marker){
    Wait-Window
    $taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
    try {
        try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(10))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
        if(!$taskHeld){throw 'UE asset production gate remained occupied.'}
        Wait-Window
        $taskLog=Join-Path $taskRoot ($Script+'-'+$taskStamp+'.log')
        $taskReceipt.state='producing_'+$Script;$taskReceipt.logs[$Script]=$taskLog;Write-Receipt
        $taskScript=Join-Path $taskRoot ($Script+'.py')
        & (Join-Path $taskEngine 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskScript" -unattended -nop4 -nosplash -nosound -nullrhi -multiprocess -DDC=InstalledNoZenLocalFallback "-abslog=$taskLog"
        $taskExit=$LASTEXITCODE
        $taskText=[IO.File]::ReadAllText($taskLog)
        if($taskExit -ne 0 -or !$taskText.Contains($Marker)){throw "Asset production incomplete: $Script exit=$taskExit; $taskLog"}
        $taskReceipt[$Script]='Saved';Write-Receipt
    } finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
}
try {
    Write-Receipt
    if($Stage -in @('Build','All')){Build-Target 'FPSGAMEEditor';Build-Target 'FPSGAME'}
    if($Stage -in @('Assets','All')){Produce-Assets 'author_local_gas' 'M10_LOCAL_GAS_V8_ASSETS_SAVED'}
    $taskReceipt.state='requested_production_stages_completed';Write-Receipt
    Write-Output 'M10 Local Gas V8 production stages completed. Runtime remains untested. Editor/game were not launched.'
} catch {$taskReceipt.state='blocked_or_failed';$taskReceipt['error']=$_.Exception.Message;Write-Receipt;throw}
