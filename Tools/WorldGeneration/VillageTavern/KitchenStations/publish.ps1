param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$root=(Resolve-Path "$PSScriptRoot/../../../..").Path
$liveRel='Content/WorldGeneration/VillageTavern/KitchenStations'
$live=Join-Path $root $liveRel
$stage=Join-Path "$root/Saved/TavernKitchenStations" ([Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path "$stage/Content","$stage/Config" -Force|Out-Null
$original=@{}
if(Test-Path -LiteralPath $live){
    foreach($file in Get-ChildItem -LiteralPath $live -File){$original[$file.Name]=(Get-FileHash -LiteralPath $file.FullName).Hash}
}
$groups=@(
    @('WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials','M_VillageR2_Oak.*'),
    @('WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces','T_ChapelTimber_*'),
    @('WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces','M_CarpenterSawn.*'),
    @('WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces','M_CarpenterIron.*'),
    @('WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces','M_CarpenterCut.*'),
    @('WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces','M_CarpenterRot.*'),
    @('WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces','T_CarpenterCut_*'),
    @('WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces','T_CarpenterMetal_RHAOM.*'),
    @('UnrealNormandy/Textures','T_MetalRust_00A_*'),
    @('UnrealNormandy/Textures','T_RottenWoodSurface_00A_*'),
    @('UnrealNormandy/Textures','T_WoodSurface_00A_*'),
    @('WorldGeneration/VillageTavern/Furniture','M_TavernOiledOak.*'),
    @('WorldGeneration/VillageTavern/Service','T_Kiln*'),
    @('WorldGeneration/VillageTavern/Service','M_TavernStoneware.*'),
    @('WorldGeneration/VillageTavern/Service','MI_TavernClay.*'),
    @('WorldGeneration/VillageTavern/Service','MI_TavernAshGlaze.*')
)
foreach($group in $groups){
    $target=Join-Path "$stage/Content" $group[0]
    New-Item -ItemType Directory -Path $target -Force|Out-Null
    Get-ChildItem -LiteralPath (Join-Path "$root/Content" $group[0]) -File -Filter $group[1]|Copy-Item -Destination $target
}
$project="$stage/KitchenStations.uproject"
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(@{Name='PythonScriptPlugin';Enabled=$true},
    @{Name='EditorScriptingUtilities';Enabled=$true})}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $project -Encoding UTF8
'[ConsoleVariables]','Interchange.FeatureFlags.Import.FBX=0'|Set-Content -LiteralPath "$stage/Config/DefaultEngine.ini" -Encoding UTF8
$exe="$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
& $exe $project /Engine/Maps/Entry -run=pythonscript "-script=$PSScriptRoot/import_stations.py" -unattended -nsightaftermath=0 -nop4 -nosound -NullRHI -nosplash -Multiprocess -NoAssetRegistryCacheWrite -ddc=InstalledNoZenLocalFallback '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$stage/import.log" *> "$stage/console.log"
if ($LASTEXITCODE -or !(Test-Path -LiteralPath "$stage/saved.json")){throw "Kitchen station commandlet failed: $stage/import.log"}
$files=foreach($name in (Get-Content -LiteralPath "$stage/saved.json" -Raw|ConvertFrom-Json)){
    Get-Item -LiteralPath "$stage/$liveRel/$name.uasset"
    Get-ChildItem -LiteralPath "$stage/$liveRel" -File|Where-Object {$_.BaseName -ceq $name -and $_.Extension -in '.uexp','.ubulk','.uptnl'}
}
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$mutex.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    foreach($file in $files){
        $target=Join-Path $live $file.Name
        $hash=if(Test-Path -LiteralPath $target){(Get-FileHash -LiteralPath $target).Hash}
        if($hash -ne $original[$file.Name]){throw "Kitchen package changed while building: $target"}
    }
    if($original.Count -and (Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -match '(?i)FPSGAME(?:\.uproject|[" ]|$)'})){
        $guard=Join-Path $stage 'loaded_stations.py'
        @'
import json, pathlib, unreal
root = pathlib.Path(__file__).resolve().parent
names = json.loads((root/'saved.json').read_text(encoding='utf8'))
for name in names:
    path='/Game/WorldGeneration/VillageTavern/KitchenStations/'+name+'.'+name
    if unreal.find_object(None,path):
        raise RuntimeError('The editor already holds '+path)
'@ | Set-Content -LiteralPath $guard -Encoding UTF8
        & "$root/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $guard
        if($LASTEXITCODE){throw 'Active editor holds a target package.'}
    }
    New-Item -ItemType Directory -Path $live -Force|Out-Null
    foreach($file in $files){
        $target=Join-Path $live $file.Name
        $temp=$target+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
        [IO.File]::Copy($file.FullName,$temp,$false)
        if([IO.File]::Exists($target)){
            [IO.File]::Replace($temp,$target,[NullString]::Value)
        }else{
            [IO.File]::Move($temp,$target)
        }
    }
    Copy-Item -LiteralPath "$stage/saved.json" -Destination "$root/SourceAssets/HillsVillageTavern/KitchenStations/saved.json" -Force
    Write-Output "Published $($files.Count) kitchen station packages."
} finally {
    if($held){$mutex.ReleaseMutex()}
    $mutex.Dispose()
}
