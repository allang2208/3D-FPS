param([ValidateRange(1,3600)][int]$QueueWaitSeconds=180)
$ErrorActionPreference='Stop'
$stockProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$stockScript=Join-Path $PSScriptRoot 'import_model.py'
$stockEngine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$stockStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$stockOutput=Join-Path $stockProject "SourceAssets/LegendaryStock20261006/import-$stockStamp.txt"
$stockEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
if($stockEditors.Count){
    & (Join-Path $stockProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $stockScript -QueueWaitSeconds $QueueWaitSeconds -OutputFile $stockOutput -MaxOutputChars 3000
    exit $LASTEXITCODE
}
$stockGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$stockHeld=$false
try {
    try {$stockHeld=$stockGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))}
    catch [Threading.AbandonedMutexException] {$stockHeld=$true}
    if(-not $stockHeld){throw 'UE authoring batch busy; no commandlet started.'}
    $stockProcesses=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
    if($stockProcesses.Count){throw 'FPSGAME became active; retain source and use the existing editor bridge.'}
    $stockLog=Join-Path $stockProject "SourceAssets/LegendaryStock20261006/import-$stockStamp.log"
    & $stockEngine (Join-Path $stockProject 'FPSGAME.uproject') -run=pythonscript "-script=$stockScript" -NullRHI -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$stockLog" *> $stockOutput
    if($LASTEXITCODE -ne 0){Get-Content -LiteralPath $stockOutput -Tail 20;throw "Tactical stock import failed: $stockLog"}
    Write-Output "TACTICAL_STOCK_ASSETS_SAVED $stockLog"
} finally {
    if($stockHeld){$stockGate.ReleaseMutex()}
    $stockGate.Dispose()
}
