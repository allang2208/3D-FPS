$ErrorActionPreference='Stop'
$captureProject='D:/FPS3D/FPSGAME'
$captureWork=Join-Path $captureProject 'SourceAssets/KaitlinPlayer20261023'
$captureStamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$captureLog=Join-Path $captureWork ('capture-'+$captureStamp+'.log')
$captureOut=Join-Path $captureWork ('capture-'+$captureStamp+'.stdout.txt')
$captureGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$captureHeld=$false
try {
    Write-Output 'Queued for the equipment source capture batch.'
    try {$captureHeld=$captureGate.WaitOne()} catch [Threading.AbandonedMutexException] {$captureHeld=$true}
    while($true) {
        $captureBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
                ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if(-not $captureBusy.Count) {break}
        try {Wait-Process -Id $captureBusy[0].ProcessId -Timeout 45 -ErrorAction Stop}
        catch [System.TimeoutException] {}
        catch {if(Get-Process -Id $captureBusy[0].ProcessId -ErrorAction SilentlyContinue) {throw}}
    }
    $captureTotal=(Get-Content -LiteralPath (Join-Path $captureWork 'FitInputs/inventory.json') -Raw | ConvertFrom-Json).meshes.Count
    $captureBatch=0
    do {
        $captureBatchLog=$captureLog.Replace('.log',('-'+$captureBatch+'.log'))
        $captureBatchOut=$captureOut.Replace('.txt',('-'+$captureBatch+'.txt'))
        Write-Output ('Equipment source log: '+$captureBatchLog)
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' (Join-Path $captureProject 'FPSGAME.uproject') '-run=pythonscript' ( '-script='+ (Join-Path $captureProject 'Tools/KaitlinPlayer/extract_fit_inputs.py')) '-KaitlinCaptureAll' '-unattended' '-nop4' '-nosplash' '-nosound' '-nullrhi' ('-abslog='+$captureBatchLog) *> $captureBatchOut
        $captureResult=$LASTEXITCODE
        Write-Output ('Equipment source exit='+$captureResult)
        Get-Content -LiteralPath $captureBatchOut -Tail 4
        if($captureResult -ne 0) {exit $captureResult}
        $captureStatus=Get-Content -LiteralPath (Join-Path $captureWork 'FitInputs/capture_status.json') -Raw | ConvertFrom-Json
        Write-Output ('Equipment source remaining='+$captureStatus.remaining)
        $captureBatch++
    } while(-not $captureStatus.complete)
} finally {
    if($captureHeld) {$captureGate.ReleaseMutex()}
    $captureGate.Dispose()
}
