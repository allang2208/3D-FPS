$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$out = Join-Path $project 'SourceAssets/HillsVillageCarpenter/Props'
$stage = Join-Path $out 'AuthoringHost'
New-Item -ItemType Directory -Force -Path $stage | Out-Null
@{
    FileVersion = 3
    EngineAssociation = '5.8'
    Plugins = @(@{Name='PythonScriptPlugin'; Enabled=$true},@{Name='EditorScriptingUtilities'; Enabled=$true})
} | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath "$stage/CarpenterProps.uproject" -Encoding utf8
# Stage read-only sources by package name. Only the dedicated output namespace is published.
$sourceGroups = @(
    @('WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces','T_ChapelTimber_*'),
    @('WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials','M_VillageR2_Oak.*'),
    @('UnrealNormandy/Textures','T_LS_BlackAlderBark_00A_*'),
    @('UnrealNormandy/Textures','T_WoodSurface_00A_*'),
    @('UnrealNormandy/Textures','T_RottenWoodSurface_00A_*'),
    @('UnrealNormandy/Textures','T_MetalRust_00A_*')
)
foreach($group in $sourceGroups){
    $base = Join-Path "$project/Content" $group[0]
    $target = Join-Path "$stage/Content" $group[0]
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    Get-ChildItem -LiteralPath $base -File -Filter $group[1] | ForEach-Object {
        if(-not (Test-Path -LiteralPath (Join-Path $target $_.Name))){
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $target $_.Name)
        }
    }
}
$env:UE_SKIP_UBT_SDK_SETUP='1'
$exe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
& $exe "$stage/CarpenterProps.uproject" -run=pythonscript "-script=$PSScriptRoot/import_props.py" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' '-ExecCmds=Interchange.FeatureFlags.Import.FBX 0' "-abslog=$out/import.log" *> "$out/import.console.log"
if($LASTEXITCODE -ne 0){throw "UE carpenter import failed ($LASTEXITCODE)"}
$receipt=Get-Content -Raw "$out/saved.json" | ConvertFrom-Json
$paths=@()
foreach($package in $receipt.packages){
    if(-not $package.StartsWith('/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/')){throw "Outside carpenter asset directory: $package"}
    $rel='Content/'+$package.Substring(6)+'.uasset'
    $src=Join-Path $stage $rel
    $dst=Join-Path $project $rel
    if(Test-Path -LiteralPath $dst){
        if((Get-FileHash -LiteralPath $src).Hash -ne (Get-FileHash -LiteralPath $dst).Hash){throw "Existing asset at $dst"}
        continue
    }
    $paths+=@([pscustomobject]@{source=$src;destination=$dst})
}
foreach($pair in $paths){
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $pair.destination) | Out-Null
    $tmp=$pair.destination+'.carpenter.tmp'
    [IO.File]::Copy($pair.source,$tmp,$true)
    [IO.File]::Move($tmp,$pair.destination)
}
$receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$out/installed.json" -Encoding utf8
