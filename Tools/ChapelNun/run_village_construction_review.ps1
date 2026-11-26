param([string]$Attempt='first')
$ErrorActionPreference='Stop'
$villageProject='D:/FPS3D/FPSGAME'
$villageRun="$villageProject/Saved/VillageConstructionReview20261117/$Attempt"
if(Test-Path -LiteralPath $villageRun){throw "Run already exists: $villageRun"}
$villageHost="$villageRun/Host"
New-Item -ItemType Directory -Path "$villageHost/Binaries/Win64","$villageRun/Saved/SaveGames","$villageRun/Evidence","$villageRun/Intermediate" -Force | Out-Null
Copy-Item -LiteralPath "$villageProject/FPSGAME.uproject" -Destination "$villageHost/FPSGAME.uproject"
Copy-Item -LiteralPath "$villageProject/Config" -Destination "$villageHost/Config" -Recurse
foreach($villageFolder in 'Content','Plugins','Shaders'){
 if(Test-Path -LiteralPath "$villageProject/$villageFolder"){New-Item -ItemType Junction -Path "$villageHost/$villageFolder" -Target "$villageProject/$villageFolder" | Out-Null}
}
foreach($villageName in 'CachedAssetRegistry','CachedAssetRegistryDiscovery.bin'){
 if(Test-Path -LiteralPath "$villageProject/Intermediate/$villageName"){Copy-Item -LiteralPath "$villageProject/Intermediate/$villageName" -Destination "$villageRun/Intermediate/$villageName" -Recurse}
}
$villageArgs=@(('"'+$villageHost+'/FPSGAME.uproject"'),'/Game/GameMaps/L_TemperateHills_Initial',
 '-game','-RenderOffscreen','-windowed','-ResX=1920','-ResY=1080','-ForceRes','-unattended','-nosound','-nosplash',
 '-ClearwaterNoMenu','-SkipStartupMenu','-VillageConstructionReview','-ChapelReview','-HillsNewWorld','-HillsSeed=122',
 '-ColdSteelProfile=VillageConstructionReview','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
 '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
 ('-UserDir="'+$villageRun+'"'),('-abslog="'+$villageRun+'/runtime.log"'),('-VillageConstructionOut="'+$villageRun+'/Evidence"'),
 '-ExecCmds="t.MaxFPS 30,DisableAllScreenMessages,fps.Test.VillageConstructionReview"',
 '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
 '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False',
 '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorLoadingSavingSettings]:bAutoSaveEnable=False',
 '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False')
$villageGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$villageHeld=$false
try{
 try{$villageHeld=$villageGate.WaitOne()}catch [Threading.AbandonedMutexException]{$villageHeld=$true}
 while($true){
  $villageBusy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
  if(-not $villageBusy.Count){break}
  try{Wait-Process -Id $villageBusy[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $villageBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
 }
 foreach($villageName in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules'){Copy-Item -LiteralPath "$villageProject/Binaries/Win64/$villageName" -Destination "$villageHost/Binaries/Win64/$villageName"}
 $villageJob=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $villageArgs -WindowStyle Hidden -PassThru -RedirectStandardOutput "$villageRun/stdout.log" -RedirectStandardError "$villageRun/stderr.log"
 $villageHandle=$villageJob.Handle
 @{pid=$villageJob.Id;run=$villageRun;args=$villageArgs;module_sha256=(Get-FileHash -LiteralPath "$villageHost/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash}|ConvertTo-Json -Depth 4|Set-Content -LiteralPath "$villageRun/launch.json" -Encoding utf8
 Write-Output "VILLAGE_REVIEW_PID=$($villageJob.Id) RUN=$villageRun"
 $villageJob.WaitForExit()
 @{exit_code=$villageJob.ExitCode;finished_at=(Get-Date).ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath "$villageRun/exit.json" -Encoding utf8
 if(Test-Path -LiteralPath "$villageRun/Evidence/result.json"){Get-Content -LiteralPath "$villageRun/Evidence/result.json" -Raw}else{throw 'Missing review receipt; see runtime.log'}
}finally{if($villageHeld){$villageGate.ReleaseMutex()};$villageGate.Dispose()}
