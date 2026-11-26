param([string]$Script=(Join-Path $PSScriptRoot 'stone_relief_materials.py'),[switch]$Inspect)
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$run=Join-Path 'F:/FPSGAMEData/ArtProduction/VillageMasonry/SurfaceRelief' (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
$rel='WorldGeneration/TemperateHills/VillageMasonry/Relief'
New-Item -ItemType Directory -Force "$run/Content/$rel","$run/Config" | Out-Null
New-Item -ItemType Junction -Path "$run/Content/UnrealNormandy" -Target "$project/Content/UnrealNormandy"|Out-Null
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})} | ConvertTo-Json -Depth 4|Set-Content -Encoding utf8NoBOM "$run/Relief.uproject"
@('[ConsoleVariables]','r.VirtualTextures=1','r.AllowStaticLighting=0')|Set-Content "$run/Config/DefaultEngine.ini"
$env:VILLAGE_RELIEF_WORK=$run
$cmd='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$argsList=@(('"'+$run+'/Relief.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',('-script="'+$Script+'"'),'-unattended','-nullrhi','-nosplash','-nosound','-nop4','-Multiprocess','-NoAssetRegistryCacheWrite','-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache','-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen',
    '-ini:Engine:[VirtualTextureChunkDDCCache]:Path=F:/FPSGAMEData/Caches/DerivedDataCache/VT',('-abslog="'+$run+'/author.log"'))
$p=Start-Process -FilePath $cmd -ArgumentList $argsList -PassThru -Wait -WindowStyle Hidden
$receipt=if($Inspect){'inspect.json'}else{'saved.json'}
if($p.ExitCode -ne 0 -or !(Test-Path "$run/$receipt")) {Select-String "$run/author.log" -Pattern 'LogPython: Error|Fatal error'|Select-Object -Last 12;throw "Surface material authoring failed: $run"}
if(!$Inspect){
 $configSections=foreach($line in (Get-Content "$project/Config/DefaultEngine.ini")){
    if($line -match '^\['){$keep=$line -in '[/Script/Engine.RendererSettings]','[/Script/WindowsTargetPlatform.WindowsTargetSettings]'}
    if($keep){$line}
 }
 $configSections |Set-Content -Encoding utf8NoBOM "$run/Config/DefaultEngine.ini"
 $argsList=@(('"'+$run+'/Relief.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',('-script="'+$PSScriptRoot+'/stone_relief_materials_compile.py"'),'-AllowCommandletRendering','-RenderOffscreen','-d3d12','-sm6','-unattended','-nosplash','-nosound','-nop4','-Multiprocess','-NoAssetRegistryCacheWrite','-corelimit=6','-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache','-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen',
 '-ini:Engine:[VirtualTextureChunkDDCCache]:Path=F:/FPSGAMEData/Caches/DerivedDataCache/VT',('-abslog="'+$run+'/compiler-sm6.log"'))
 $p=Start-Process -FilePath $cmd -ArgumentList $argsList -PassThru -Wait -WindowStyle Hidden
 if($p.ExitCode -ne 0 -or !(Test-Path "$run/sm6.json")){
  Select-String "$run/compiler-sm6.log" -Pattern 'Failed to compile Material|Missing function input|LogPython: Error|error X'|Select-Object -First 12
  throw "Surface material compilation failed: $run"
 }
 $dest="$project/Content/$rel"
 $gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
 try{try{$null=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{}
  New-Item -Type Directory -Force $dest|Out-Null
  foreach($m in (Get-Content "$run/saved.json" -Raw|ConvertFrom-Json).packages){
   $file=(Split-Path $m -Leaf)+'.uasset';$dst=Join-Path $dest $file
   Copy-Item -LiteralPath "$run/Content/$rel/$file" -Destination "$dst.$PID.tmp"
   [IO.File]::Move("$dst.$PID.tmp",$dst,$true)
  }
 }finally{$gate.ReleaseMutex();$gate.Dispose()}
 Copy-Item "$run/saved.json" "$run/published.json"
}
Write-Output "$run/$receipt"

