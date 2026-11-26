param([Parameter(Mandatory)][string]$Run)
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$rel='Content/WorldGeneration/TemperateHills/HotOil/FlowR2'
$roles='M_OilBody','M_OilBubble','M_OilFilm','M_OilStream'
New-Item -ItemType Directory -Path "$Run/$rel","$Run/Config" -Force | Out-Null
$src=Join-Path $project 'Content'
$dst=Join-Path $Run 'Content'
foreach($branch in 'WorldGeneration','TemperateHills','HotOil','FlowR2'){
    foreach($dir in Get-ChildItem -LiteralPath $src -Directory){
        $target=Join-Path $dst $dir.Name
        if($dir.Name -ne $branch -and !(Test-Path -LiteralPath $target)){
            New-Item -ItemType Junction -Path $target -Target $dir.FullName | Out-Null
        }
    }
    $src=Join-Path $src $branch
    $dst=Join-Path $dst $branch
}
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(@{Name='GeometryScripting';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true},@{Name='PythonScriptPlugin';Enabled=$true})} |
    ConvertTo-Json -Depth 4 | Set-Content "$Run/Workshop.uproject" -Encoding utf8
@('[ConsoleVariables]','r.VirtualTextures=1','r.AllowStaticLighting=0') | Set-Content "$Run/Config/DefaultEngine.ini"
$cmd='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$argsList=@(('"'+$Run+'/Workshop.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',('-script="'+$PSScriptRoot+'/author_oil_materials.py"'),
    '-NullRHI','-corelimit=3','-nosound','-nosplash','-nop4','-unattended','-Multiprocess','-NoAssetRegistryCacheWrite','-AssetGatherAll=false',
    '-ini:Engine:[SystemSettings]:Editor.AsyncStaticMeshCompilation=0','-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache',
    '-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen','-ini:Engine:[VirtualTextureChunkDDCCache]:Path=F:/FPSGAMEData/Caches/DerivedDataCache/VT',('-abslog="'+$Run+'/author.log"'))
$result=Start-Process $cmd -ArgumentList $argsList -WindowStyle Hidden -Wait -PassThru
if($result.ExitCode -ne 0 -or !(Test-Path "$Run/surface-saved.json")){throw "Hot oil material authoring failed: $Run/author.log"}
New-Item -ItemType Directory -Path "$project/$rel" -Force | Out-Null
$files=@($roles | ForEach-Object {"$_.uasset"})
foreach($file in $files){
    $live=Join-Path "$project/$rel" $file
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $live) | Out-Null
    Copy-Item -LiteralPath "$Run/$rel/$file" -Destination "$live.$PID.pending"
    if(Test-Path -LiteralPath $live){
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent "$Run/Before/$rel/$file") | Out-Null
        $previous=Join-Path "$Run/Before/$rel" $file
        if(!(Test-Path -LiteralPath $previous)){Copy-Item -LiteralPath $live -Destination $previous}
        [IO.File]::Move("$live.$PID.pending",$live,$true)
    } else { [IO.File]::Move("$live.$PID.pending",$live) }
}
Copy-Item -LiteralPath "$Run/surface-saved.json" -Destination "$Run/published.json"
