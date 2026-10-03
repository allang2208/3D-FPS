param([int]$QueueWaitSeconds=300)
$ErrorActionPreference='Stop'
$partRoot=$PSScriptRoot
$projectRoot=[IO.Path]::GetFullPath((Join-Path $partRoot '../../../..'))
$pythonScript=Join-Path $partRoot 'import_assets.py'
$icon=Join-Path $partRoot 'Icons/ue_tang_dao_pommel_yanling_breaker.png'
if (-not (Test-Path -LiteralPath $icon -PathType Leaf)) { throw 'The final pommel icon must be created before saving the asset batch.' }
$editorProcess=Get-Process UnrealEditor -ErrorAction SilentlyContinue
if ($editorProcess) {
    # Use the existing editor's bridge and its whole-batch mutex. Never launch
    # another commandlet against packages loaded by this editor.
    & (Join-Path $projectRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $pythonScript -QueueWaitSeconds $QueueWaitSeconds -RequestTimeoutSeconds 300 -OutputFile (Join-Path $partRoot ('import-bridge-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.json')) -MaxOutputChars 2000
    exit $LASTEXITCODE
}
# New packages only. Use the bridge's same gate for the entire headless save.
$assetGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$acquired=$false
try {
    try { $acquired=$assetGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) }
    catch [Threading.AbandonedMutexException] { $acquired=$true;throw 'The previous UE batch ended unexpectedly. This batch preserved its files and did not run.' }
    if (-not $acquired) { Write-Output 'The UE asset batch is still busy; this batch was not run.';exit 75 }
    # If an editor opened while this batch was queued, release the gate and use
    # its normal bridge rather than starting an independent asset writer.
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
        $assetGate.ReleaseMutex();$acquired=$false
        & (Join-Path $projectRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $pythonScript -QueueWaitSeconds $QueueWaitSeconds -RequestTimeoutSeconds 300 -OutputFile (Join-Path $partRoot ('import-bridge-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.json')) -MaxOutputChars 2000
        exit $LASTEXITCODE
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' (Join-Path $projectRoot 'FPSGAME.uproject') -run=pythonscript "-script=$pythonScript" -unattended -nosplash -NoSound "-abslog=$partRoot/import.log" *> (Join-Path $partRoot 'import-console.log')
    exit $LASTEXITCODE
} finally {
    if ($acquired) { $assetGate.ReleaseMutex() }
    $assetGate.Dispose()
}
