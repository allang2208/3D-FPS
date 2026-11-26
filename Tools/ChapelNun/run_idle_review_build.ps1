$ErrorActionPreference='Stop'
$nunProject='D:/FPS3D/FPSGAME'
$nunRoot="$nunProject/SourceAssets/ChapelNun20261115/IdleBackReviewR2"
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
foreach($nunTarget in @('FPSGAMEEditor')) {
 $nunLog="$nunRoot/Logs/$nunTarget-build.log"
 $nunCommand='""E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat" '+$nunTarget+' Win64 Development "-Project='+$nunProject+'/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBA -NoUBALocal -NoXGE -NoSNDBS -NoFASTBuild -MaxParallelActions=2 "-Log='+$nunLog+'""'
 $nunProcess=Start-Process -FilePath $env:ComSpec -ArgumentList @('/d','/s','/c',$nunCommand) -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput "$nunRoot/Logs/$nunTarget-build-stdout.log" -RedirectStandardError "$nunRoot/Logs/$nunTarget-build-stderr.log"
 $nunExit=$nunProcess.ExitCode
 @{target=$nunTarget;exit_code=$nunExit;log=$nunLog;finished_at=(Get-Date).ToString('o');runtime_tested=$false}|ConvertTo-Json|Set-Content -LiteralPath "$nunRoot/$nunTarget-build.json" -Encoding utf8
 if($nunExit -ne 0){exit $nunExit}
}

} finally {if($nunHeld){$nunGate.ReleaseMutex()};$nunGate.Dispose()}
