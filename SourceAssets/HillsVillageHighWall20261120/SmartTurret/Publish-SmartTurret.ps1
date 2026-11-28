param([Parameter(Mandatory)][string]$Run)
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$rel='Content/WorldGeneration/TemperateHills/HighVillageDefense/SmartTurret'
$roles='SM_SmartTurretBase','SM_SmartTurretYaw','SM_SmartTurretCradle','SM_SmartTurretSlide','SM_SmartTurretPreview'

New-Item -ItemType Directory -Path "$Run/$rel/Materials","$Run/$rel/Textures","$Run/Config" -Force | Out-Null
$src=Join-Path $project 'Content'
$dst=Join-Path $Run 'Content'
foreach($branch in 'WorldGeneration','TemperateHills','HighVillageDefense','SmartTurret'){
    foreach($dir in Get-ChildItem -LiteralPath $src -Directory -ErrorAction SilentlyContinue){
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
@('[ConsoleVariables]','r.VirtualTextures=1','r.AllowStaticLighting=0') | Set-Content "$Run/Config/DefaultEngine.ini" -Encoding ascii

$cmd='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$argsList=@(('"'+$Run+'/Workshop.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',('-script="'+$PSScriptRoot+'/import_turret.py"'),
    '-NullRHI','-nosound','-nosplash','-nop4','-unattended','-Multiprocess','-NoAssetRegistryCacheWrite','-AssetGatherAll=false',
    '-ini:Engine:[SystemSettings]:Editor.AsyncStaticMeshCompilation=0','-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache',
    '-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen','-ini:Engine:[VirtualTextureChunkDDCCache]:Path=F:/FPSGAMEData/Caches/DerivedDataCache/VT',('-abslog="'+$Run+'/author.log"'))
$result=Start-Process $cmd -ArgumentList $argsList -WindowStyle Hidden -Wait -PassThru
if($result.ExitCode -ne 0 -or !(Test-Path "$Run/turret-saved.json")){throw "SmartTurret authoring failed: $Run/author.log"}

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
Get-ChildItem -Path "$Run/$rel/Materials","$Run/$rel/Textures" -Recurse -Filter '*.uasset' -ErrorAction SilentlyContinue | ForEach-Object {
    $sub = $_.FullName.Substring($Run.Length).TrimStart('\','/')
    Publish-Asset $sub
}
Copy-Item -LiteralPath "$Run/turret-saved.json" -Destination "$Run/published.json" -Force
Write-Output 'TURRET_PUBLISH_OK'
