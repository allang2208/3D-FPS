param([string]$ReceiptName='build-01')
$ErrorActionPreference='Stop'
$robeProject='D:/FPS3D/FPSGAME'
$robeRoot=Join-Path $robeProject 'SourceAssets/SimpleSlingBag20261022'
$robeGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$robeHeld=$false
try {
    Write-Output 'Queued for shared build window; existing builds finish first.'
    try {$robeHeld=$robeGate.WaitOne()} catch [Threading.AbandonedMutexException] {$robeHeld=$true}
    while($true){
        # Isolated import/diagnostic projects use their own project modules.
        # Only an engine process loading this checkout blocks its DLL build.
        $robeBusy=@(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -match 'D:[\\/]FPS3D[\\/]FPSGAME[\\/]FPSGAME\.uproject') -or
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if(-not $robeBusy.Count){break}
        if(@($robeBusy | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)'}).Count){Write-Output 'Existing editor preserved; base DLL build needs an available window.';exit 75}
        try {Wait-Process -Id $robeBusy[0].ProcessId -Timeout 45 -ErrorAction Stop} catch [System.TimeoutException] {} catch {if(Get-Process -Id $robeBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    foreach($robeTarget in @('FPSGAMEEditor','FPSGAME')){
        $robeLog=Join-Path $robeRoot ($ReceiptName+'-'+$robeTarget+'.log')
        $robeOut=Join-Path $robeRoot ($ReceiptName+'-'+$robeTarget+'.txt')
        & dotnet 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll' $robeTarget Win64 Development "-Project=$robeProject/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 "-Log=$robeLog" *> $robeOut
        $robeExit=$LASTEXITCODE;Get-Content -LiteralPath $robeOut -Tail 7
        if($robeExit -ne 0){exit $robeExit}
    }
} finally {if($robeHeld){$robeGate.ReleaseMutex()};$robeGate.Dispose()}
