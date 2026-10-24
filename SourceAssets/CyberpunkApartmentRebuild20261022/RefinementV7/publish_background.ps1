param([int]$BuildProcessId=0,[int]$MaximumWaitSeconds=7200,[string]$RunName='publish-01')
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskProjectPattern='(?i)D:[\\/]FPS3D[\\/]FPSGAME[\\/]FPSGAME\.uproject(?:["\s]|$)'
$taskOutput=Join-Path $taskRoot 'SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV7'
if($BuildProcessId -gt 0 -and (Get-Process -Id $BuildProcessId -ErrorAction SilentlyContinue)){Wait-Process -Id $BuildProcessId}
foreach($taskTarget in @('FPSGAMEEditor','FPSGAME')) {
    $taskBuild=Get-Content -LiteralPath "$taskOutput/build-$taskTarget.json" -Raw | ConvertFrom-Json
    if($taskBuild.exit_code -ne 0){throw "Native build remains incomplete: $taskTarget"}
}
if(-not (Test-Path -LiteralPath "$taskOutput/T_AP7_CityReflection.dds")){throw 'Production reflection texture remains incomplete.'}
$taskDeadline=[DateTime]::UtcNow.AddSeconds($MaximumWaitSeconds)
do {
    $taskProcesses=@(Get-CimInstance Win32_Process)
    if($taskProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match $taskProjectPattern}){throw 'Preserving the open editor; publish through its existing bridge.'}
    $taskOwners=@($taskProcesses | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match $taskProjectPattern)})
    if(-not $taskOwners.Count){break}
    if([DateTime]::UtcNow -gt $taskDeadline){throw 'Existing binary owner retained; publish not started.'}
    Start-Sleep -Seconds 8
}while($true)
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch remains occupied; publish not started.'}
    $taskOwners=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match $taskProjectPattern) -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
    if($taskOwners.Count){throw 'Preserving a new binary owner; publish not started.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskOutput/publish.py" -unattended -nosplash -nosound -nullrhi "-abslog=$taskOutput/$RunName.log" *> "$taskOutput/$RunName-console.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;game_run=$false;editor_opened=$false;log="$taskOutput/$RunName.log"} | ConvertTo-Json | Set-Content -LiteralPath "$taskOutput/$RunName.json" -Encoding utf8
    if($taskExit -ne 0){throw 'Apartment asset/map publishing failed; see saved commandlet log.'}
    Write-Output 'Apartment assets and map saved.'
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
