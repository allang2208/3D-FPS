param([string]$Script='read_charge_sources.py',[int]$QueueSeconds=3600)
$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$chargeOut=$PSScriptRoot
$chargeDeadline=(Get-Date).AddSeconds($QueueSeconds)
function Get-OccupiedProject {
 @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
  [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine.Replace('\','/').ToLowerInvariant().Contains('d:/fps3d/fpsgame')
 })
}
function Get-NativeBuilds {
 @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'UnrealBuildTool'})
}
$chargeGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$chargeHeld=$false
try {
 while (-not $chargeHeld) {
  if ((Get-Date) -gt $chargeDeadline) {throw 'Charge asset access occupied; source preserved.'}
  if ((Get-NativeBuilds).Count -gt 0) {Start-Sleep -Seconds 5;continue}
  try {$chargeHeld=$chargeGate.WaitOne(1000)}
  catch [Threading.AbandonedMutexException] {$chargeHeld=$true;throw 'Previous batch abandoned; no asset operation sent.'}
 }
 $chargeProcesses=@(Get-OccupiedProject)
 $chargeInteractive=@($chargeProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine.Replace('\','/').ToLowerInvariant().Contains('d:/fps3d/fpsgame/fpsgame.uproject')})
 if ($chargeInteractive.Count -eq 1 -and $chargeProcesses.Count -eq 1) {
  & (Join-Path $projectRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript (Join-Path $chargeOut $Script) -QueueWaitSeconds 0 -OutputFile (Join-Path $chargeOut ('batch-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff')+'.txt')) -MaxOutputChars 2500
  if ($LASTEXITCODE -ne 0) {throw 'Charge asset batch failed; active editor preserved.'}
 } elseif ($chargeProcesses.Count -eq 0) {
  $chargeStamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
  $chargeLog=Join-Path $chargeOut ($Script+'-'+$chargeStamp+'.log')
  $chargeArguments=@(($projectRoot+'\FPSGAME.uproject'),'-run=pythonscript',('-script='+$chargeOut+'\'+$Script),'-unattended','-nop4','-nosplash','-nosound','-nullrhi','-multiprocess','-DDC=InstalledNoZenLocalFallback',('-abslog='+$chargeLog))
  & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' @chargeArguments *> (Join-Path $chargeOut ($Script+'-'+$chargeStamp+'-console.txt'))
  $chargeExit=$LASTEXITCODE
  @{script=$Script;exit_code=$chargeExit;log=$chargeLog} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $chargeOut ($Script+'-result.json')) -Encoding utf8BOM
  if ($chargeExit -ne 0) {throw ('Charge commandlet failed: '+$chargeExit+'; '+$chargeLog)}
 } else {throw 'Project instances occupy asset access; no competing commandlet started.'}
 Write-Output ('SLAG_V14_ASSET_BATCH_COMPLETE '+$Script)
} finally {
 if ($chargeHeld) {$chargeGate.ReleaseMutex()}
 $chargeGate.Dispose()
}