$ErrorActionPreference='Stop'
$taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
for($taskAttempt=0;$taskAttempt -lt 20 -and -not $taskHeld;$taskAttempt++){
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(30))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
}
if(-not $taskHeld){throw 'Asset/build batch remains busy; no build started.'}
$taskCommandlets=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object {(-not $_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
foreach($taskCommandlet in $taskCommandlets){$taskProcess=Get-Process -Id $taskCommandlet.ProcessId -ErrorAction SilentlyContinue;if($taskProcess -and -not $taskProcess.WaitForExit(600000)){throw 'Existing commandlet still owns the DLL; no build started.'}}
$taskEditor=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^UnrealEditor' -and ((-not $_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject') })
if($taskEditor.Count -gt 0){throw 'Preserve the running editor/commandlet; full DLL build requires it to finish or close.'}
while(@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'UnrealBuildTool.dll'}).Count -gt 0){Start-Sleep -Seconds 5}
$taskLog=Join-Path $PSScriptRoot ('build-'+$taskStamp+'.log')
$taskOutput=Join-Path $PSScriptRoot ('build-'+$taskStamp+'-console.log')
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 "-Log=$taskLog" *> $taskOutput
$taskCode=$LASTEXITCODE
[ordered]@{target='FPSGAMEEditor';exit_code=$taskCode;log=$taskLog;finished=(Get-Date).ToString('o');gameplay_tested=$false}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $PSScriptRoot ('build-'+$taskStamp+'-receipt.json')) -Encoding utf8
Get-Content -LiteralPath $taskOutput -Tail 15
exit $taskCode
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
