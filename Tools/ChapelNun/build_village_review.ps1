$ErrorActionPreference='Stop'
$nunProject='D:/FPS3D/FPSGAME'
$nunRoot="$nunProject/Saved/VillageConstructionReview20261117/BuildR3"
New-Item -ItemType Directory -Path "$nunRoot/Logs" -Force | Out-Null
$nunGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$nunHeld=$false
try {
 try {$nunHeld=$nunGate.WaitOne()} catch [Threading.AbandonedMutexException] {$nunHeld=$true}
while($true) {
 $nunBusy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
 if(-not $nunBusy.Count){break}
 Write-Output 'Waiting for the current authoring/build process to finish.'
 try {Wait-Process -Id $nunBusy[0].ProcessId -Timeout 45 -ErrorAction Stop} catch [System.TimeoutException] {} catch {if(Get-Process -Id $nunBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
}
foreach($nunTarget in @('FPSGAMEEditor','FPSGAME')) {
 $nunLog="$nunRoot/Logs/$nunTarget-build.log"
 $nunCommand='""E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat" '+$nunTarget+' Win64 Development "-Project='+$nunProject+'/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -ForceHeaderGeneration -NoUBA -NoUBALocal -NoXGE -NoSNDBS -NoFASTBuild -MaxParallelActions=2 "-Log='+$nunLog+'""'
 $nunProcess=Start-Process -FilePath $env:ComSpec -ArgumentList @('/d','/s','/c',$nunCommand) -WindowStyle Hidden -PassThru -RedirectStandardOutput "$nunRoot/Logs/$nunTarget-build-stdout.log" -RedirectStandardError "$nunRoot/Logs/$nunTarget-build-stderr.log"
 $nunHandle=$nunProcess.Handle
 # Keep only this invocation's compiler children at normal priority: BelowNormal
 # was starved by other normal-priority work on this machine during the first build.
 while(-not $nunProcess.WaitForExit(3000)) {
  $villageUbt=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object { $_.CommandLine -like "*$nunLog*" })
  foreach($villageOwner in $villageUbt) {
   foreach($villageChild in @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($villageOwner.ProcessId) AND Name='cl.exe'")) {
    $villageCompiler=Get-Process -Id $villageChild.ProcessId -ErrorAction SilentlyContinue
    if($villageCompiler -and $villageCompiler.PriorityClass -eq 'BelowNormal') {
     try {$villageCompiler.PriorityClass='Normal'} catch [System.InvalidOperationException] {}
    }
   }
  }
 }
 $nunProcess.WaitForExit()
 $nunExit=$nunProcess.ExitCode
 if($null -eq $nunExit){throw "Build process exit code is unavailable."}
 @{target=$nunTarget;exit_code=$nunExit;log=$nunLog;finished_at=(Get-Date).ToString('o');runtime_tested=$false}|ConvertTo-Json|Set-Content -LiteralPath "$nunRoot/$nunTarget-build.json" -Encoding utf8
 if($nunExit -ne 0){exit $nunExit}
}

} finally {if($nunHeld){$nunGate.ReleaseMutex()};$nunGate.Dispose()}
