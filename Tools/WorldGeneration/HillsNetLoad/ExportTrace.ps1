param([Parameter(Mandatory=$true)][string]$Run,[ValidateSet('host','client','late')][string]$Role='client',[double]$Start=-1,[double]$End=-1,[string]$Thread='GameThread')
$ErrorActionPreference='Stop'
$trace=Join-Path $Run "$Role.utrace"
if(-not(Test-Path -LiteralPath $trace)){throw "Trace missing: $trace"}
$out=Join-Path $Run ('Trace-'+$Role)
New-Item -ItemType Directory -Force -Path $out|Out-Null
$rsp=Join-Path $out 'export.rsp'
if($Start -lt 0){
 $commands=@(
  "TimingInsights.ExportThreads $out/threads.csv",
  "TimingInsights.ExportTimers $out/timers.csv",
  "TimingInsights.ExportTimingEvents $out/frames.csv -threads=GameThread -timers=FEngineLoop::Tick -columns=ThreadId,TimerId,TimerName,StartTime,EndTime,Duration,Depth")
}else{
 $label=if($Thread -eq 'GameThread'){''}else{($Thread -replace '[^a-zA-Z0-9]','_')+'-'}
 $commands=@("TimingInsights.ExportTimingEvents $out/events-$label$Start-$End.csv -threads=`"$Thread`" -startTime=$Start -endTime=$End -columns=ThreadId,TimerId,TimerName,StartTime,EndTime,Duration,Depth")
}
[IO.File]::WriteAllLines($rsp,[string[]]$commands,[Text.UTF8Encoding]::new($false))
$args=@(('-OpenTraceFile="'+$trace+'"'),('-ABSLOG="'+$out+'/export.log"'),'-AutoQuit','-NoUI',('-ExecOnAnalysisCompleteCmd="@='+$rsp+'"'))
$p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealInsights.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
$handle=$p.Handle
$p.WaitForExit()
@{pid=$p.Id;exit_code=$p.ExitCode;trace=$trace;commands=$commands}|ConvertTo-Json -Depth 4|Set-Content -LiteralPath "$out/export-result.json"
if($p.ExitCode -ne 0){throw 'Trace export failed'}
Write-Output "HILLS_TRACE_EXPORTED $out"
