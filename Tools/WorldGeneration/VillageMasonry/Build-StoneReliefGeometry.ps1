param([switch]$SurveyOnly, [string]$Work='F:/FPSGAMEData/ArtProduction/VillageStoneRelief/Geometry')
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$run=Join-Path $Work (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
$src=Join-Path $project 'Content'
$dst=Join-Path $run 'Content'
New-Item -ItemType Directory -Path "$run/Config",$dst -Force | Out-Null
foreach($branch in 'WorldGeneration','TemperateHills','VillageMasonry'){
    foreach($directory in Get-ChildItem -LiteralPath $src -Directory){
        if($directory.Name -ne $branch){ New-Item -ItemType Junction -Path (Join-Path $dst $directory.Name) -Target $directory.FullName | Out-Null }
    }
    $src=Join-Path $src $branch
    $dst=Join-Path $dst $branch
    New-Item -ItemType Directory -Path $dst | Out-Null
}
Get-ChildItem -LiteralPath $src -File -Filter 'SM_*.uasset' | Copy-Item -Destination $dst
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(@{Name='GeometryScripting';Enabled=$true},@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})} |
    ConvertTo-Json -Depth 4 | Set-Content "$run/StoneRelief.uproject" -Encoding utf8
@('[ConsoleVariables]','r.VirtualTextures=1','r.AllowStaticLighting=0') | Set-Content "$run/Config/DefaultEngine.ini" -Encoding utf8
$env:STONE_RELIEF_GEOMETRY_WORK=$run
$env:STONE_RELIEF_GEOMETRY_SURVEY=if($SurveyOnly){'1'}else{'0'}
$env:STONE_RELIEF_NUMPY=(python -c "import pathlib,numpy;print(pathlib.Path(numpy.__file__).resolve().parents[1])").Trim()
$cmd='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$argsList=@(('"'+$run+'/StoneRelief.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',('-script="'+$PSScriptRoot+'/stone_relief_geometry.py"'),'-NullRHI','-unattended','-nosplash','-nosound','-nop4','-Multiprocess','-NoAssetRegistryCacheWrite','-AssetGatherAll=false','-ini:Engine:[SystemSettings]:Editor.AsyncStaticMeshCompilation=0','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorExperimentalSettings]:bEnableAsyncStaticMeshCompilation=False','-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache','-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen',
    '-ini:Engine:[VirtualTextureChunkDDCCache]:Path=F:/FPSGAMEData/Caches/DerivedDataCache/VT',('-abslog="'+$run+'/author.log"'))
$proc=Start-Process -FilePath $cmd -ArgumentList $argsList -Wait -PassThru -WindowStyle Hidden
if($proc.ExitCode -ne 0 -or !(Test-Path -LiteralPath "$run/saved.json")){
    Select-String "$run/author.log" -Pattern 'LogPython: Error|Fatal error' | Select-Object -Last 14
    throw "Geometry authoring incomplete at $run"
}
if($SurveyOnly){Write-Output "$run/saved.json";return}
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try{$held=$mutex.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    $receipt=Get-Content "$run/saved.json" -Raw | ConvertFrom-Json
    foreach($mesh in $receipt.meshes){
        $rel=$mesh.destination.Substring(6)+'.uasset'
        $destination=Join-Path "$project/Content" $rel
        New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force | Out-Null
        $tmp="$destination.$PID.new"
        Copy-Item -LiteralPath (Join-Path "$run/Content" $rel) -Destination $tmp
        if(Test-Path -LiteralPath $destination){[IO.File]::Replace($tmp,$destination,(Join-Path $run ((Split-Path $destination -Leaf)+'.previous')))}
        else{[IO.File]::Move($tmp,$destination)}
    }
}finally{if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
Copy-Item -LiteralPath "$run/saved.json" -Destination "$run/published.json"
Write-Output "$run/published.json"
