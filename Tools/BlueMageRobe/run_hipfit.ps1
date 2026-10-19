param([string]$ReceiptName='hipfit-build-01')
$ErrorActionPreference='Stop'
$robeProject='D:/FPS3D/FPSGAME'
$robeRoot=Join-Path $robeProject 'SourceAssets/BlueMageRobe20261018'
$robeGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$robeHeld=$false
try {
    Write-Output 'Queued for shared build window; existing builds finish first.'
    try {$robeHeld=$robeGate.WaitOne()} catch [Threading.AbandonedMutexException] {$robeHeld=$true}
    while($true){
        $robeBusy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if(-not $robeBusy.Count){break}
        if(@($robeBusy | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)'}).Count){Write-Output 'Existing editor preserved; base DLL build needs an available window.';exit 75}
        try {Wait-Process -Id $robeBusy[0].ProcessId -Timeout 45 -ErrorAction Stop} catch [System.TimeoutException] {} catch {if(Get-Process -Id $robeBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    foreach($robeTarget in @('FPSGAMEEditor','FPSGAME')){
        $robeLog=Join-Path $robeRoot ($ReceiptName+'-'+$robeTarget+'.log')
        $robeOut=Join-Path $robeRoot ($ReceiptName+'-'+$robeTarget+'.txt')
        & dotnet 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll' $robeTarget Win64 Development "-Project=$robeProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 "-Log=$robeLog" *> $robeOut
        $robeExit=$LASTEXITCODE;Get-Content -LiteralPath $robeOut -Tail 7
        if($robeExit -ne 0){exit $robeExit}
    }

    $hipOut=Join-Path $robeRoot ('HipFit20261019/'+$ReceiptName+'-assets.txt')
    $hipLog=Join-Path $robeRoot ('HipFit20261019/'+$ReceiptName+'-assets.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$robeProject/FPSGAME.uproject" '-run=pythonscript' "-script=$robeProject/Tools/BlueMageRobe/save_hipfit.py" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$hipLog" *> $hipOut
    $hipExit=$LASTEXITCODE;Get-Content -LiteralPath $hipOut -Tail 9
    if($hipExit -ne 0){exit $hipExit}
    & python -X utf8 "$robeProject/Tools/BlueMageRobe/publish_hipfit.py"
    if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
} finally {if($robeHeld){$robeGate.ReleaseMutex()};$robeGate.Dispose()}
