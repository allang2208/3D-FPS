param([string]$OutputRoot='D:/FPS3D/FPSGAME/Saved/VillageDefenses20261117/Build07')
$ErrorActionPreference='Stop'
$plantProject='D:/FPS3D/FPSGAME'
$plantRoot=$OutputRoot
New-Item -ItemType Directory -Path "$plantRoot/Logs" -Force | Out-Null
$plantGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$plantHeld=$false
try {
 try {$plantHeld=$plantGate.WaitOne()} catch [Threading.AbandonedMutexException] {$plantHeld=$true}
foreach($plantTarget in @('FPSGAMEEditor','FPSGAME')) {
while($true) {
 # A previous UBT may exit before its Build.bat launcher releases the script
 # lock. Include the launcher so this queue does not race another pending job.
 $plantBusy=@(Get-CimInstance Win32_Process | Where-Object {
  $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','FPSGAME.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or
  ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
  ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build\.bat')
 })
 if(-not $plantBusy.Count){break}
 Write-Output 'Waiting for the current authoring/build process to finish.'
 try {Wait-Process -Id $plantBusy[0].ProcessId -Timeout 45 -ErrorAction Stop} catch [System.TimeoutException] {} catch {if(Get-Process -Id $plantBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
}
 $plantLog="$plantRoot/Logs/$plantTarget-build.log"
 $plantCommand='""E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat" '+$plantTarget+' Win64 Development "-Project='+$plantProject+'/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -NoUBALocal -NoXGE -NoSNDBS -NoFASTBuild -MaxParallelActions=2 "-Log='+$plantLog+'""'
 $plantProcess=Start-Process -FilePath $env:ComSpec -ArgumentList @('/d','/s','/c',$plantCommand) -WindowStyle Hidden -PassThru -RedirectStandardOutput "$plantRoot/Logs/$plantTarget-build-stdout.log" -RedirectStandardError "$plantRoot/Logs/$plantTarget-build-stderr.log"
 $plantHandle=$plantProcess.Handle
 # Keep only this invocation's compiler children at normal priority: BelowNormal
 # was starved by other normal-priority work on this machine during the first build.
 while(-not $plantProcess.WaitForExit(3000)) {
  $villageUbt=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object { $_.CommandLine -like "*$plantLog*" })
  foreach($villageOwner in $villageUbt) {
   foreach($villageChild in @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($villageOwner.ProcessId) AND Name='cl.exe'")) {
    $villageCompiler=Get-Process -Id $villageChild.ProcessId -ErrorAction SilentlyContinue
    if($villageCompiler -and $villageCompiler.PriorityClass -eq 'BelowNormal') {
     try {$villageCompiler.PriorityClass='Normal'} catch [System.InvalidOperationException] {}
    }
   }
  }
 }
 $plantProcess.WaitForExit()
 $plantExit=$plantProcess.ExitCode
 if($null -eq $plantExit){throw "Build process exit code is unavailable."}
 @{target=$plantTarget;exit_code=$plantExit;log=$plantLog;finished_at=(Get-Date).ToString('o');runtime_tested=$false}|ConvertTo-Json|Set-Content -LiteralPath "$plantRoot/$plantTarget-build.json" -Encoding utf8
 if($plantExit -ne 0){exit $plantExit}
}

} finally {if($plantHeld){$plantGate.ReleaseMutex()};$plantGate.Dispose()}
