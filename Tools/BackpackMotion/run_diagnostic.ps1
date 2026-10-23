param([string]$ReceiptName='three-pack-response-r2',
    [ValidateSet('OtherPacks','Motion','Lifecycle','Capacity')][string]$Mode='OtherPacks')
$ErrorActionPreference='Stop'
$packProject='D:/FPS3D/FPSGAME'
$packDir=Join-Path $packProject 'Saved/BackpackMotionDiagnosis20261022'
[IO.Directory]::CreateDirectory($packDir)|Out-Null
$packGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$packHeld=$false
try {
    try {$packHeld=$packGate.WaitOne()} catch [Threading.AbandonedMutexException] {$packHeld=$true}
    while($true){
        $packBusy=@(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -match 'D:[\\/]FPS3D[\\/]FPSGAME[\\/]FPSGAME\.uproject') -or
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if(-not $packBusy.Count){break}
        if(@($packBusy | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count){throw 'Existing editor preserved; isolated native diagnostic needs an available window.'}
        try {Wait-Process -Id $packBusy[0].ProcessId -Timeout 45 -ErrorAction Stop} catch [System.TimeoutException] {} catch {if(Get-Process -Id $packBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    $packLog=Join-Path $packDir ($ReceiptName+'.log')
    [string[]]$packArguments=switch($Mode){
        'OtherPacks' {@('-MotionOnly','-OtherPacks')}
        'Motion' {@('-MotionOnly')}
        'Lifecycle' {@('-LifecycleOnly')}
        'Capacity' {@('-SyntheticOnly')}
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$packProject/FPSGAME.uproject" -run=BackpackCapacityAudit @packArguments -unattended -nop4 -nosplash -AllowCommandletRendering -RenderOffscreen "-abslog=$packLog" *> (Join-Path $packDir ($ReceiptName+'.stdout.log'))
    $packExit=$LASTEXITCODE
    Get-Content -LiteralPath $packLog -Tail 8
    exit $packExit
} finally {if($packHeld){$packGate.ReleaseMutex()};$packGate.Dispose()}
