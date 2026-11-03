$ErrorActionPreference='Stop'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss';$run=Join-Path $PSScriptRoot ('Packaged-'+$stamp)
$package=Join-Path $PSScriptRoot 'Package/Windows';$exe=Join-Path $package 'FPSGAME/Binaries/Win64/FPSGAME.exe'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false;$peer=$null
New-Item -ItemType Directory -Path $run | Out-Null
try {
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch occupied.'}
    if(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.ThreadCount -gt 0) -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')}){throw 'Runtime/build busy.'}
    if((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory -lt 5MB){throw 'Less than 5 GiB free before packaged NullRHI scenario.'}
    # Only the diagnostic standalone entry changed after the successful cook.
    # Keep the cooked containers intact and install the current Game build.
    Copy-Item -LiteralPath 'D:/FPS3D/FPSGAME/Binaries/Win64/FPSGAME.exe' -Destination $exe -Force
    $args=@('"/Engine/Maps/Entry?game=/Script/FPSGAME.ThunderHammerClosureGameMode"','-nullrhi','-nosound','-unattended','-nosplash','-ThunderHammerClosureAudit','-SkipStartupMenu','-ThunderClosureStandalone',
      '-DPCVars=fps.body.AsyncPreload=0,fps.body.WorldBodySuppress=1',('-ColdSteelProfile=SkillNetworkAudit_TCP_'+$stamp),
      ('-UserDir="'+$run.Replace('\','/')+'/User/"'),('-ThunderClosureOutput="'+$run+'/result.json"'),('-abslog="'+$run+'/engine.log"'),'-ExecCmds="t.MaxFPS 60,t.IdleWhenNotForeground 0"')
    $peer=Start-Process -FilePath $exe -WorkingDirectory $package -ArgumentList $args -WindowStyle Hidden -PassThru
    @{pid=$peer.Id;arguments=$args;exe=$exe;exe_sha256=(Get-FileHash $exe).Hash;scope='packaged standalone NullRHI; no network or rendered acceptance'}|ConvertTo-Json -Depth 4|Set-Content "$run/launch.json" -Encoding utf8
    Write-Output "THUNDER_PACKAGED_STARTED PID=$($peer.Id) PATH=$run"
    $until=(Get-Date).AddSeconds(600);$low=0
    while(-not $peer.WaitForExit(2000)){
        if((Get-Date) -gt $until){throw 'Packaged scenario timed out.'}
        if((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory -lt 1MB){$low++}else{$low=0}
        if($low -ge 3){throw 'Packaged scenario interrupted below 1 GiB free.'}
    }
    $result=Get-Content "$run/result.json" -Raw|ConvertFrom-Json
    $ok=$peer.ExitCode -eq 0 -and $result.passed
    @{passed=$ok;exit_code=$peer.ExitCode;run=$run;scope='packaged standalone NullRHI; cooked containers unchanged after diagnostic-only executable update'}|ConvertTo-Json|Set-Content "$run/receipt.json" -Encoding utf8
    Write-Output "THUNDER_PACKAGED_DONE PASS=$ok PATH=$run";if(-not $ok){exit 1}
}catch {
    @{passed=$false;error=$_.Exception.Message;run=$run}|ConvertTo-Json|Set-Content "$run/runner-error.json" -Encoding utf8
    throw
}finally {
    if($peer -and -not $peer.HasExited){$live=Get-CimInstance Win32_Process -Filter "ProcessId=$($peer.Id)";if($live.CommandLine -like '*-ThunderClosureStandalone*' -and $live.CommandLine -like ('*'+$stamp+'*')){Stop-Process -Id $peer.Id}}
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
