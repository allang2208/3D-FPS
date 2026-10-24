param([string]$Run='build-01')
$ErrorActionPreference='Stop'
$apRoot='D:/FPS3D/FPSGAME';$apOut="$apRoot/SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV21"
New-Item -ItemType Directory -Force -Path $apOut | Out-Null
$apGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$apHeld=$false
try {
 Write-Output 'Waiting once for the shared UE build window.'
 try{$apHeld=$apGate.WaitOne([TimeSpan]::FromHours(2))}catch [Threading.AbandonedMutexException]{$apHeld=$true}
 if(-not $apHeld){throw 'Shared UE window remained busy'}
 $apDeadline=[DateTime]::UtcNow.AddHours(2)
 while($true){
  $apProcesses=@(Get-CimInstance Win32_Process)
  if($apProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -like '*FPSGAME.uproject*'}){throw 'Save and close the active FPSGAME editor; no process was stopped'}
  $apBusy=@($apProcesses | Where-Object {$_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -like '*FPSGAME.uproject*')})
  if(-not $apBusy.Count){break}
  if([DateTime]::UtcNow -gt $apDeadline){throw 'Existing build retained'}
  Start-Sleep -Seconds 5
 }
 foreach($apTarget in @('FPSGAMEEditor','FPSGAME')){
  & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $apTarget Win64 Development "-Project=$apRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=4 "-Log=$apOut/$Run-$apTarget.log" *> "$apOut/$Run-$apTarget-console.log"
  $apCode=$LASTEXITCODE
  @{target=$apTarget;exit_code=$apCode;completed=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$apOut/$Run-$apTarget.json" -Encoding utf8
  if($apCode -ne 0){throw "$apTarget build failed; see this batch log"}
  Write-Output "$apTarget build completed."
 }
} finally {if($apHeld){$apGate.ReleaseMutex()};$apGate.Dispose()}
