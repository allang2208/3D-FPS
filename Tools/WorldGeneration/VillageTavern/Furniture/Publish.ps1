param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8', [switch]$DiningFinishOnly)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$stage=Join-Path $env:TEMP ('FPSGAME-TavernFurniture-'+[Guid]::NewGuid().ToString('N'))
$hostContent=Join-Path $stage 'Content'
$config=Join-Path $stage 'Config'
New-Item -ItemType Directory -Path $hostContent,$config -Force | Out-Null
$project=Join-Path $stage 'TavernFurniture.uproject'
@{
    FileVersion=3
    EngineAssociation='5.8'
    Plugins=@(@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $project -Encoding UTF8
'[ConsoleVariables]', 'Interchange.FeatureFlags.Import.FBX=0' |
    Set-Content -LiteralPath (Join-Path $config 'DefaultEngine.ini') -Encoding UTF8

# Copy only the rural material dependency closure into the isolated content mount.
$inputGroups=@(
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
    @('UnrealNormandy/Textures','T_WoodSurface_00A_*')
)
foreach($group in $inputGroups){
    $from=Join-Path "$root/Content" $group[0]
    $to=Join-Path $hostContent $group[0]
    New-Item -ItemType Directory -Force -Path $to | Out-Null
    Get-ChildItem -LiteralPath $from -File -Filter $group[1] | Copy-Item -Destination $to
}
$stageScript=Join-Path $PSScriptRoot 'stage_existing.py'
if ($DiningFinishOnly) {
    & python $stageScript $root $stage 'dining-finish'
} else {
    & python $stageScript $root $stage
}
if($LASTEXITCODE -ne 0){throw "Could not stage existing furniture in $stage"}
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    # The private host only reads its own input copies. Acquire the shared editor
    # batch lock at the point where finished packages enter the real project.
    $exe=Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $scriptName = if ($DiningFinishOnly) {'import_dining_finish.py'} else {'import_furniture.py'}
    $jobArgs=@(('"'+$project+'"'),'-run=pythonscript',('-script="'+$PSScriptRoot+'/'+$scriptName+'"'),
        '-unattended','-nop4','-nosplash','-nosound','-NullRHI','-Multiprocess','-NoAssetRegistryCacheWrite',
        '-LocalDataCachePath=D:/FPS3D/DerivedDataCache',('-abslog="'+$stage+'/import.log"'))
    $oldSkip=$env:UE_SKIP_UBT_SDK_SETUP
    try {
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        $process=Start-Process -FilePath $exe -ArgumentList $jobArgs -WindowStyle Hidden -PassThru
        $null=$process.Handle
        Write-Output "Importing tavern furniture in $stage"
        $process.WaitForExit()
        $process.Refresh()
        if($process.ExitCode -ne 0){throw "Furniture commandlet exited with $($process.ExitCode). $stage/import.log"}
    } finally { $env:UE_SKIP_UBT_SDK_SETUP=$oldSkip }
    $paths=Get-Content -LiteralPath "$stage/saved.json" -Raw | ConvertFrom-Json
    $original=Get-Content -LiteralPath "$stage/original.json" -Raw | ConvertFrom-Json
    $payloads=Get-Content -LiteralPath "$stage/original-payloads.json" -Raw | ConvertFrom-Json
    $backup=Join-Path "$root/Saved/TavernReview/Furniture" ('UE-'+[IO.Path]::GetFileName($stage))
    try { $held=$mutex.WaitOne() } catch [Threading.AbandonedMutexException] { $held=$true }
    $projectEditor=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" |
        Where-Object {$_.CommandLine -match '(?i)FPSGAME(?:\.uproject|[" ]|$)'}
    if($projectEditor){
        $guard=Join-Path $stage 'loaded_furniture.py'
        $root | Set-Content -LiteralPath (Join-Path $stage 'project-root.txt') -Encoding UTF8
        @'
import json, unreal
from pathlib import Path
stage = Path(__file__).resolve().parent
expected = Path((stage/'project-root.txt').read_text(encoding='utf-8-sig').strip()).resolve()
actual = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
if actual != expected:
    raise RuntimeError('Connected editor is using ' + str(actual))
targets = json.loads((stage/'saved.json').read_text(encoding='utf-8'))
loaded = [p for p in targets if unreal.find_object(None,p + '.' + p.rsplit('/',1)[1])]
if loaded:
    raise RuntimeError('Loaded furniture must be updated inside the existing editor: ' + ', '.join(loaded))
'@ | Set-Content -LiteralPath $guard -Encoding UTF8
        & (Join-Path $root 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $guard
        if($LASTEXITCODE -ne 0){throw "The active editor could not release the target packages for file publication"}
    }
    $targetDirectory=Join-Path $root 'Content/WorldGeneration/VillageTavern/Furniture'
    New-Item -ItemType Directory -Force -Path $targetDirectory | Out-Null
    $files=@()
    foreach($path in $paths){
        $name=[IO.Path]::GetFileName($path)
        if($path -cne "/Game/WorldGeneration/VillageTavern/Furniture/$name" -or
            $name -cnotin $original.PSObject.Properties.Name){
            throw "Invalid furniture output $path"
        }
        foreach($ext in '.ubulk','.uexp','.uptnl','.uasset'){
            $file=$name+$ext
            $target=Join-Path $targetDirectory $file
            $staged=Join-Path $hostContent ($path.Substring(6)+$ext)
            $hash=if(Test-Path -LiteralPath $target){(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash}
            $expected=if($ext -eq '.uasset'){$original.$name}else{$payloads.$file}
            if($hash -ne $expected){throw "Furniture changed after staging: $target"}
            $written=[IO.File]::Exists($staged)
            if($ext -eq '.uasset' -and -not $written){throw "Missing staged furniture $staged"}
            if($hash -or $written){
                $files+=@{Target=$target;Source=$staged;Backup=(Join-Path $backup $file);Existed=[bool]$hash;Written=$written}
            }
        }
    }
    New-Item -ItemType Directory -Path $backup | Out-Null
    $done=@()
    try {
        foreach($f in $files){
            $temporary=$f.Target+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
            try {
                # Content can be a junction to another volume. Retain the original
                # in Saved by copying; the atomic swap itself stays beside the asset.
                if($f.Existed){[IO.File]::Copy($f.Target,$f.Backup,$false)}
                if($f.Written){
                    [IO.File]::Copy($f.Source,$temporary,$false)
                    if($f.Existed){[IO.File]::Replace($temporary,$f.Target,[NullString]::Value)}
                    else {[IO.File]::Move($temporary,$f.Target)}
                } else {[IO.File]::Delete($f.Target)}
                $done+=$f
            } finally {if([IO.File]::Exists($temporary)){[IO.File]::Delete($temporary)}}
            Write-Output "Saved $($f.Target)"
        }
    } catch {
        foreach($f in $done){
            if($f.Existed){
                $restore=$f.Target+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
                [IO.File]::Copy($f.Backup,$restore,$false)
                if($f.Written){[IO.File]::Replace($restore,$f.Target,[NullString]::Value)}
                else {[IO.File]::Move($restore,$f.Target)}
            } else {[IO.File]::Delete($f.Target)}
        }
        throw
    }
    if (-not $DiningFinishOnly) {
        Copy-Item -LiteralPath "$stage/saved.json" -Destination "$PSScriptRoot/saved.json" -Force
    }
    if (-not $DiningFinishOnly) {
        Copy-Item -LiteralPath "$stage/mesh-report.json" -Destination (Join-Path $backup 'mesh-report.json')
    }
} finally {
    if($held){$mutex.ReleaseMutex()}
    $mutex.Dispose()
}
