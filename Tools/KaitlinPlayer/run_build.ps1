param([string]$ReceiptName=('build-'+(Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference='Stop'
$kaitlinProject='D:/FPS3D/FPSGAME'
$kaitlinRoot=Join-Path $kaitlinProject 'SourceAssets/KaitlinPlayer20261023'
$kaitlinGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$kaitlinHeld=$false
try {
    Write-Output 'Queued for shared build window; existing builds finish first.'
    try {$kaitlinHeld=$kaitlinGate.WaitOne()} catch [Threading.AbandonedMutexException] {$kaitlinHeld=$true}
    while($true){
        $kaitlinBusy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if(-not $kaitlinBusy.Count){break}
        if(@($kaitlinBusy | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)'}).Count){Write-Output 'Existing editor preserved; base DLL build needs an available window.';exit 75}
        try {Wait-Process -Id $kaitlinBusy[0].ProcessId -Timeout 45 -ErrorAction Stop} catch [System.TimeoutException] {} catch {if(Get-Process -Id $kaitlinBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    foreach($kaitlinTarget in @('FPSGAMEEditor','FPSGAME')){
        $kaitlinLog=Join-Path $kaitlinRoot ($ReceiptName+'-'+$kaitlinTarget+'.log')
        $kaitlinOut=Join-Path $kaitlinRoot ($ReceiptName+'-'+$kaitlinTarget+'.txt')
        & dotnet 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll' $kaitlinTarget Win64 Development "-Project=$kaitlinProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 "-Log=$kaitlinLog" *> $kaitlinOut
        $kaitlinExit=$LASTEXITCODE;Get-Content -LiteralPath $kaitlinOut -Tail 7
        if($kaitlinExit -ne 0){exit $kaitlinExit}
    }
} finally {if($kaitlinHeld){$kaitlinGate.ReleaseMutex()};$kaitlinGate.Dispose()}
