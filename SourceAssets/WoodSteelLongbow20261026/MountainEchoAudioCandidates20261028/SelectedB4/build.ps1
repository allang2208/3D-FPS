param([string[]]$Targets=@('FPSGAMEEditor','FPSGAME'))
$ErrorActionPreference='Stop'
$bowProject='D:/FPS3D/FPSGAME'
$bowGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$bowHeld=$false
try {
try {$bowHeld=$bowGate.WaitOne([TimeSpan]::FromHours(1))} catch [Threading.AbandonedMutexException] {$bowHeld=$true}
if(-not $bowHeld){throw 'Asset/build batch is busy; no build started.'}
foreach($bowTarget in $Targets) {
    $bowAnnounced=$false
    while($true){
        $bowBusy=@(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe' -or
            ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build\.bat') -or $_.Name -eq 'UnrealEditor-Cmd.exe'
        })
        if(-not $bowBusy.Count){break}
        if(-not $bowAnnounced){Write-Output 'Waiting for the running build or asset commandlet.';$bowAnnounced=$true}
        Start-Sleep -Seconds 5
    }
    $bowProcessNames=if($bowTarget -eq 'FPSGAMEEditor'){@('UnrealEditor','FPSGAME')}else{@('FPSGAME')}
    $bowLoaded=@(Get-Process -Name $bowProcessNames -ErrorAction SilentlyContinue)
    if($bowLoaded.Count){Write-Output 'Primary editor or game is open; preserve it and defer binary replacement.';exit 75}
    $bowLog=Join-Path $PSScriptRoot ('build-'+$bowTarget+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $bowTarget Win64 Development `
        ('-Project='+$bowProject+'/FPSGAME.uproject') -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 `
        ('-Log='+(Join-Path $PSScriptRoot ('ubt-'+$bowTarget+'.log'))) *> $bowLog
    $bowResult=$LASTEXITCODE
    @{target=$bowTarget;exit_code=$bowResult;log=$bowLog;game_run=$false;finished=(Get-Date).ToString('s')} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot ('build-'+$bowTarget+'.json')) -Encoding utf8
    Get-Content -LiteralPath $bowLog -Tail 10
    if($bowResult -ne 0){exit $bowResult}
}
} finally {if($bowHeld){$bowGate.ReleaseMutex()};$bowGate.Dispose()}
