param()
$ErrorActionPreference='Stop'
$env:UE_SKIP_UBT_SDK_SETUP='1'
$project='D:/FPS3D/ThunderHammerFullReviewHost20261102'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss';$run=Join-Path $PSScriptRoot ('Visual-'+$stamp)
New-Item -ItemType Directory -Path $run | Out-Null
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false;$peer=$null
try {
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch busy; capture not started.'}
    if(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.ThreadCount -gt 0) -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')}){throw 'Runtime/build busy; capture not started.'}
    if((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory -lt 12MB){throw 'Less than 12 GiB free before single-process capture; no process started.'}
    $args=@(('"'+$project+'/FPSGAME.uproject"'),'"/Engine/Maps/Entry?game=/Script/FPSGAME.ThunderHammerClosureGameMode"','-game','-RenderOffscreen','-unattended','-nosplash','-NoLiveCoding','-AssetGatherAll=false','-ThunderHammerClosureAudit','-SkipStartupMenu',
      '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
      '-DPCVars=fps.body.AsyncPreload=0','-asyncassetcompilationmaxconcurrency=1',
      ('-ColdSteelProfile=SkillNetworkAudit_TCV_'+$stamp),('-UserDir="'+$run.Replace('\','/')+'/User/"'),
      ('-ThunderClosureCapture="'+$run.Replace('\','/')+'/Frames"'),('-ThunderClosureOutput="'+$run+'/result.json"'),
      ('-abslog="'+$run+'/engine.log"'),'-ExecCmds="t.MaxFPS 60,r.VSync 0"')
    $peer=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
    @{pid=$peer.Id;arguments=$args;resolution='read actual PNG dimensions, RenderOffscreen may ignore ResX/ResY'}|ConvertTo-Json -Depth 3|Set-Content "$run/launch.json" -Encoding utf8
    Write-Output "THUNDER_VISUAL_STARTED PID=$($peer.Id) PATH=$run"
    $until=(Get-Date).AddSeconds(900);$lowMemory=0
    while(-not $peer.WaitForExit(2000)){
        if((Get-Date) -gt $until){throw 'Capture timed out.'}
        if((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory -lt 1MB){$lowMemory++}else{$lowMemory=0}
        if($lowMemory -ge 3){throw 'Capture interrupted: available physical memory stayed below 1 GiB.'}
    }
    $result=Get-Content "$run/result.json" -Raw|ConvertFrom-Json
    $ok=$peer.ExitCode -eq 0 -and $result.passed
    @{passed=$ok;exit_code=$peer.ExitCode;run=$run;dll_sha256=(Get-FileHash "$project/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash}|ConvertTo-Json|Set-Content "$run/receipt.json" -Encoding utf8
    Write-Output "THUNDER_VISUAL_EXIT=$($peer.ExitCode) PATH=$run"
    if(-not $ok){exit 1}
}catch {
    @{passed=$false;error=$_.Exception.Message;run=$run}|ConvertTo-Json|Set-Content "$run/runner-error.json" -Encoding utf8
    throw
}finally {
    if($peer -and -not $peer.HasExited){$live=Get-CimInstance Win32_Process -Filter "ProcessId=$($peer.Id)";if($live.CommandLine -like '*-ThunderClosureCapture=*' -and $live.CommandLine -like ('*'+$stamp+'*')){Stop-Process -Id $peer.Id}}
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
