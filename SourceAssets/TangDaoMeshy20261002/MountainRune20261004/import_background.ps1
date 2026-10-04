param([int]$QueueWaitSeconds=900)
$ErrorActionPreference='Stop'
$partRoot=$PSScriptRoot
$projectRoot=[IO.Path]::GetFullPath((Join-Path $partRoot '../../..'))
$pythonScript=Join-Path $partRoot 'import_assets.py'
if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){
    & (Join-Path $projectRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $pythonScript -QueueWaitSeconds $QueueWaitSeconds -RequestTimeoutSeconds 300 -OutputFile (Join-Path $partRoot 'Records/import-bridge.json') -MaxOutputChars 2000
    exit $LASTEXITCODE
}
$assetGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$acquired=$false
try{
    try{$acquired=$assetGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))}
    catch [Threading.AbandonedMutexException]{$acquired=$true;throw 'Prior asset batch ended unexpectedly; this batch did not run.'}
    if(-not $acquired){Write-Output 'Asset batch busy; source retained.';exit 75}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){
        $assetGate.ReleaseMutex();$acquired=$false
        & (Join-Path $projectRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $pythonScript -QueueWaitSeconds $QueueWaitSeconds -RequestTimeoutSeconds 300 -OutputFile (Join-Path $partRoot 'Records/import-bridge.json') -MaxOutputChars 2000
        exit $LASTEXITCODE
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' (Join-Path $projectRoot 'FPSGAME.uproject') -run=pythonscript "-script=$pythonScript" -unattended -nosplash -nosound -nop4 -nullrhi -multiprocess "-abslog=$partRoot/Records/import.log" *> (Join-Path $partRoot 'Records/import-console.log')
    exit $LASTEXITCODE
}finally{
    if($acquired){$assetGate.ReleaseMutex()}
    $assetGate.Dispose()
}
