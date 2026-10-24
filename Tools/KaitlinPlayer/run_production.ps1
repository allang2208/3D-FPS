param([Parameter(Mandatory=$true)][string]$Stage)
$ErrorActionPreference='Stop'
$kaitlinProject='D:/FPS3D/FPSGAME'
$kaitlinWork=Join-Path $kaitlinProject 'SourceAssets/KaitlinPlayer20261023'
$kaitlinScript=Join-Path $kaitlinProject ('Tools/KaitlinPlayer/'+$Stage+'.py')
$kaitlinStatus=Join-Path $kaitlinWork ($Stage+'_status.json')
$kaitlinGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$kaitlinHeld=$false
$kaitlinStamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
try {
    Write-Output ('Queued Kaitlin asset production: '+$Stage)
    try {$kaitlinHeld=$kaitlinGate.WaitOne()} catch [Threading.AbandonedMutexException] {$kaitlinHeld=$true}
    $kaitlinBatch=0
    do {
        while($true) {
            $kaitlinBusy=@(Get-CimInstance Win32_Process | Where-Object {
                $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
                    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
            })
            if(-not $kaitlinBusy.Count) {break}
            try {Wait-Process -Id $kaitlinBusy[0].ProcessId -Timeout 45 -ErrorAction Stop}
            catch [System.TimeoutException] {}
            catch {if(Get-Process -Id $kaitlinBusy[0].ProcessId -ErrorAction SilentlyContinue) {throw}}
        }
        $kaitlinLog=Join-Path $kaitlinWork ($Stage+'-'+$kaitlinStamp+'-'+$kaitlinBatch+'.log')
        Write-Output ('Production log: '+$kaitlinLog)
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' (Join-Path $kaitlinProject 'FPSGAME.uproject') '-run=pythonscript' ('-script='+$kaitlinScript) '-unattended' '-nop4' '-nosplash' '-nosound' '-nullrhi' ('-abslog='+$kaitlinLog) *> ($kaitlinLog+'.stdout.txt')
        $kaitlinResult=$LASTEXITCODE
        Write-Output ('Production exit='+$kaitlinResult)
        Get-Content -LiteralPath ($kaitlinLog+'.stdout.txt') -Tail 3
        if($kaitlinResult -ne 0) {exit $kaitlinResult}
        $kaitlinProgress=Get-Content -LiteralPath $kaitlinStatus -Raw | ConvertFrom-Json
        Write-Output ('Remaining='+$kaitlinProgress.remaining)
        $kaitlinBatch++
    } while(-not $kaitlinProgress.complete)
} finally {
    if($kaitlinHeld) {$kaitlinGate.ReleaseMutex()}
    $kaitlinGate.Dispose()
}
