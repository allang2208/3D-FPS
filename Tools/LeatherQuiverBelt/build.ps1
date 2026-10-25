param([string]$ReceiptName=('belt-build-'+(Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference='Stop'
$beltProject='D:/FPS3D/FPSGAME'
$beltLogs=Join-Path $beltProject 'SourceAssets/LeatherQuiverBelt20261025/Logs'
$beltGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$beltHeld=$false
try {
    Write-Output 'Queued for the shared engine/build window.'
    try {$beltHeld=$beltGate.WaitOne()} catch [Threading.AbandonedMutexException] {$beltHeld=$true}
    while ($true) {
        $beltBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe','UnrealEditor-Cmd.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if (-not $beltBusy.Count) {break}
        try {Wait-Process -Id $beltBusy[0].ProcessId -Timeout 45 -ErrorAction Stop} catch [System.TimeoutException] {} catch {if(Get-Process -Id $beltBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    $beltEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'})
    if ($beltEditors.Count) {throw 'The project editor is open. Preserve it and compile through the existing editor.'}
    $beltResults=@()
    foreach ($beltTarget in @('FPSGAMEEditor','FPSGAME')) {
        $beltLog=Join-Path $beltLogs ($ReceiptName+'-'+$beltTarget+'.log')
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $beltTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE "-Log=$beltLog" *> (Join-Path $beltLogs ($ReceiptName+'-'+$beltTarget+'.txt'))
        $beltExit=$LASTEXITCODE
        $beltResults+=@{target=$beltTarget;exit_code=$beltExit;log=$beltLog}
        @{completed=($beltResults.Count -eq 2 -and $beltExit -eq 0);results=$beltResults;runtime_tested=$false} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $beltProject 'SourceAssets/LeatherQuiverBelt20261025/build_receipt.json') -Encoding UTF8
        Write-Output "Tactical belt build $beltTarget exit=$beltExit"
        if($beltExit -ne 0){Get-Content -LiteralPath $beltLog -Tail 25;exit $beltExit}
    }
} finally {if($beltHeld){$beltGate.ReleaseMutex()};$beltGate.Dispose()}
