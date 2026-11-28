param([Parameter(Mandatory)][string]$Run,[switch]$HandPotOnly,[switch]$SurfaceOnly)
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$rel='Content/WorldGeneration/TemperateHills/HotOil'
$roles='SM_OilHearth','SM_OilHandPot','SM_OilSurface'
if($HandPotOnly -and $SurfaceOnly){throw 'Choose one mesh subset'}
if($HandPotOnly){$roles=@('SM_OilHandPot')}
if($SurfaceOnly){$roles=@('SM_OilSurface')}
$env:VILLAGE_OIL_SURFACE_ONLY=if($SurfaceOnly){'1'}else{'0'}
$env:VILLAGE_OIL_HAND_POT_ONLY=if($HandPotOnly){'1'}else{'0'}
New-Item -ItemType Directory -Path "$Run/$rel/PropsR2/Textures","$Run/Config" -Force | Out-Null
$src=Join-Path $project 'Content'
$dst=Join-Path $Run 'Content'
foreach($branch in 'WorldGeneration','TemperateHills','HotOil'){
    foreach($dir in Get-ChildItem -LiteralPath $src -Directory){
        $target=Join-Path $dst $dir.Name
        if($dir.Name -ne $branch -and !(Test-Path -LiteralPath $target)){
            New-Item -ItemType Junction -Path $target -Target $dir.FullName | Out-Null
        }
    }
    $src=Join-Path $src $branch
    $dst=Join-Path $dst $branch
}
# The liquid disc references the saved R2 fluid; the geometry host reads those packages only.
if(!$HandPotOnly -and !(Test-Path "$Run/$rel/FlowR2")){
    New-Item -ItemType Junction -Path "$Run/$rel/FlowR2" -Target "$project/$rel/FlowR2" | Out-Null
}
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(@{Name='GeometryScripting';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true},@{Name='PythonScriptPlugin';Enabled=$true})} |
    ConvertTo-Json -Depth 4 | Set-Content "$Run/Workshop.uproject" -Encoding utf8
@('[ConsoleVariables]','r.VirtualTextures=1','r.AllowStaticLighting=0') | Set-Content "$Run/Config/DefaultEngine.ini"
$cmd='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$argsList=@(('"'+$Run+'/Workshop.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',('-script="'+$PSScriptRoot+'/import_oil.py"'),
    '-NullRHI','-nosound','-nosplash','-nop4','-unattended','-Multiprocess','-NoAssetRegistryCacheWrite','-AssetGatherAll=false',
    '-ini:Engine:[SystemSettings]:Editor.AsyncStaticMeshCompilation=0','-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache',
    '-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen','-ini:Engine:[VirtualTextureChunkDDCCache]:Path=F:/FPSGAMEData/Caches/DerivedDataCache/VT',('-abslog="'+$Run+'/author.log"'))
$result=Start-Process $cmd -ArgumentList $argsList -WindowStyle Hidden -Wait -PassThru
if($result.ExitCode -ne 0 -or !(Test-Path "$Run/oil-saved.json")){throw "Workshop authoring failed: $Run/author.log"}
New-Item -ItemType Directory -Path "$project/$rel" -Force | Out-Null

function Publish-Asset([string]$RelSubPath){
    $srcAsset = Join-Path $Run $RelSubPath
    if(!(Test-Path -LiteralPath $srcAsset)){return}
    $live = Join-Path $project $RelSubPath
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $live) | Out-Null
    Copy-Item -LiteralPath $srcAsset -Destination "$live.$PID.pending"
    if(Test-Path -LiteralPath $live){
        $prev = Join-Path "$Run/Before" $RelSubPath
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $prev) | Out-Null
        if(!(Test-Path -LiteralPath $prev)){Copy-Item -LiteralPath $live -Destination $prev}
        Move-Item -LiteralPath "$live.$PID.pending" -Destination $live -Force
    } else { Move-Item -LiteralPath "$live.$PID.pending" -Destination $live }
}

foreach($role in $roles){ Publish-Asset "$rel/$role.uasset" }
if(!$SurfaceOnly){
    Get-ChildItem -Path "$Run/$rel/PropsR2" -Recurse -Filter '*.uasset' -ErrorAction SilentlyContinue | ForEach-Object {
        $sub = $_.FullName.Substring($Run.Length).TrimStart('\','/')
        Publish-Asset $sub
    }
}
Copy-Item -LiteralPath "$Run/oil-saved.json" -Destination "$Run/published.json"
