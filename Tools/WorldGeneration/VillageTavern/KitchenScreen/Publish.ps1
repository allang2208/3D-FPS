param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$stage=Join-Path "$root/Saved/TavernKitchenScreen" ([Guid]::NewGuid().ToString('N'))
$relative='WorldGeneration/VillageTavern/KitchenScreen'
$target=Join-Path "$root/Content" $relative
$original=@{}
if(Test-Path -LiteralPath $target){
    Get-ChildItem -LiteralPath $target -File | ForEach-Object { $original[$_.Name]=(Get-FileHash $_.FullName).Hash }
}
New-Item -ItemType Directory -Force "$stage/Config","$stage/Content" | Out-Null
$project="$stage/TavernKitchenScreens.uproject"
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(
    @{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true}
)}|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $project -Encoding utf8
'[ConsoleVariables]','Interchange.FeatureFlags.Import.FBX=0'|Set-Content -LiteralPath "$stage/Config/DefaultEngine.ini" -Encoding utf8
$groups=@(
    @('WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials','M_VillageR2_Oak.*'),
    @('WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces','T_ChapelTimber_*'),
    @('WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces','M_CarpenterIron.*'),
    @('WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces','M_CarpenterCut.*'),
    @('WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces','M_CarpenterRot.*'),
    @('WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces','T_CarpenterCut_*'),
    @('WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces','T_CarpenterMetal_RHAOM.*'),
    @('UnrealNormandy/Textures','T_MetalRust_00A_*'),
    @('UnrealNormandy/Textures','T_RottenWoodSurface_00A_*'),
    @('UnrealNormandy/Textures','T_WoodSurface_00A_*'),
    @('Dungeons/TunnelStyleIncinerator20261111/Quixel/CrackedPaintedPlaster_d91bfe39/Textures','T_CrackedPaintedPlaster_*')
)
foreach($group in $groups){
    $to=Join-Path "$stage/Content" $group[0]
    New-Item -ItemType Directory -Force $to|Out-Null
    Get-ChildItem -LiteralPath (Join-Path "$root/Content" $group[0]) -File -Filter $group[1]|Copy-Item -Destination $to
}
$log="$stage/import.log"
$exe="$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
& $exe $project /Engine/Maps/Entry -run=pythonscript "-script=$PSScriptRoot/import_screens.py" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess -AssetGatherAll=false -NoAssetRegistryCacheWrite -ddc=InstalledNoZenLocalFallback '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$log" *> "$stage/console.log"
if($LASTEXITCODE -or !(Test-Path -LiteralPath "$stage/saved.json")){throw "Screen import failed. See $log"}
$names=Get-Content "$stage/saved.json" -Raw|ConvertFrom-Json
$files=foreach($name in $names){
    Get-Item -LiteralPath "$stage/Content/$relative/$name.uasset"
    Get-ChildItem -LiteralPath "$stage/Content/$relative" -File | Where-Object {$_.BaseName -eq $name -and $_.Extension -in '.ubulk','.uexp','.uptnl'}
}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try{$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    New-Item -ItemType Directory -Force $target|Out-Null
    foreach($file in $files){
        $live=Join-Path $target $file.Name
        if(Test-Path -LiteralPath $live){
            if(!$original.ContainsKey($file.Name) -or (Get-FileHash $live).Hash -ne $original[$file.Name]){
                throw "Concurrent publication at $live"
            }
        }elseif($original.ContainsKey($file.Name)){throw "Source package moved during import: $live"}
    }
    if($original.Count -and (Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'"|Where-Object {$_.CommandLine -match '(?i)FPSGAME(?:\.uproject|[" ]|$)'})){
        $guard=Join-Path $stage 'guard.py'
        @'
import json, unreal
from pathlib import Path
stage=Path(__file__).resolve().parent
base='/Game/WorldGeneration/VillageTavern/KitchenScreen/'
loaded=[name for name in json.loads((stage/'saved.json').read_text()) if unreal.find_object(None,base+name+'.'+name)]
if loaded: raise RuntimeError('Active editor holds kitchen screen packages: '+str(loaded))
'@ | Set-Content -LiteralPath $guard -Encoding utf8
        & (Join-Path $root 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $guard
        if($LASTEXITCODE -ne 0){throw 'Current editor holds a target package'}
    }
    foreach($file in $files){[IO.File]::Copy($file.FullName,(Join-Path $target $file.Name),$true)}
    Write-Output ("Saved "+($names -join ', ')+" to "+$target)
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
