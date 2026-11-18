param([string]$Attempt='udp03',[string]$Build='Build04')
$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$output="$project/Saved/HillsVillageInteractionAudit20261118/$Build"
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 try{$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
 New-Item -ItemType Directory -Force -Path "$output/Logs"|Out-Null
 $busy=Get-CimInstance Win32_Process | Where-Object { $_.Name -in 'UnrealEditor.exe','UnrealEditor-Cmd.exe','FPSGAME.exe' }
 if($busy){throw 'An engine process remains active; preserve it and retry this batch.'}
 $log="$output/Logs/FPSGAMEEditor-build.log"
 $command='""E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat" FPSGAMEEditor Win64 Development "-Project='+$project+'/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBA -NoUBALocal -NoXGE -MaxParallelActions=2 "-Log='+$log+'""'
 $p=Start-Process -FilePath $env:ComSpec -ArgumentList @('/d','/s','/c',$command) -WindowStyle Hidden -PassThru -RedirectStandardOutput "$output/Logs/stdout.log" -RedirectStandardError "$output/Logs/stderr.log"
 $handle=$p.Handle;$p.WaitForExit()
 @{target='FPSGAMEEditor';exit_code=$p.ExitCode;log=$log;finished_at=(Get-Date).ToString('o');purpose='fixture component-name correction; production Game target built in Build03'}|ConvertTo-Json|Set-Content -LiteralPath "$output/FPSGAMEEditor-build.json"
 if($p.ExitCode -ne 0){throw 'Fixture build failed'}
 # Nested scripts acquire the same mutex recursively on this PowerShell thread;
 # retain the outer batch across compilation, module copy and both network peers.
 & "$PSScriptRoot/Run.ps1" -Attempt $Attempt -Build $Build -GameBuild Build03
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
