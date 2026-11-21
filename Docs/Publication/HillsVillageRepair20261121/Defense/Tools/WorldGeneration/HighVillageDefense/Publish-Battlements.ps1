param([string]$Run = (Join-Path 'F:/FPSGAMEData/ArtProduction/VillageBattlementFit' (Get-Date -Format 'yyyyMMdd-HHmmss-fff')),
      [switch]$PublishSaved)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path "$PSScriptRoot/../../..").Path
$design = 'SourceAssets/HillsVillageHighWall20261120/Design01/Authored'
$hills = 'Content/WorldGeneration/TemperateHills'
New-Item -ItemType Directory -Force -Path "$Run/Authored","$Run/Config" | Out-Null
$env:HIGH_VILLAGE_PROJECT = $project
$env:STONE_RELIEF_GEOMETRY_WORK = $Run
$env:STONE_RELIEF_NUMPY = (py -3.11 -c 'import pathlib,numpy;print(pathlib.Path(numpy.__file__).resolve().parents[1])').Trim()
if (!(Test-Path -LiteralPath "$Run/Authored/SM_HighWall.meshzip")) {
    py -3.11 -c "import os,sys,pathlib;p=pathlib.Path(os.environ['HIGH_VILLAGE_PROJECT']);sys.path.insert(0,str(p/'Tools/WorldGeneration/HighVillageDefense'));import source_mesh,author_kit;source_mesh.OUT=pathlib.Path(os.environ['STONE_RELIEF_GEOMETRY_WORK'])/'Authored';author_kit.wall()"
    if ($LASTEXITCODE -ne 0) {throw 'Wall mesh export failed'}
}
$sourceFiles = @("$design/SM_HighWall.meshzip", "$design/fracture-saved.json")
$packages = @()
foreach ($index in -1..8) {
    $name = if ($index -lt 0) {'SM_HighWall'} else {'SM_HighWallShard_{0:00}' -f $index}
    $original = if ($index -lt 0) {'HighVillageDefense'} else {'HighVillageDefense/Fracture'}
    foreach ($folder in $original,'VillageMasonry','VillageMasonry/ReliefMeshes') {
        $packages += "$hills/$folder/$name.uasset"
    }
}
# Copy only owned packages. Mount dependencies read-only from the real project;
# no ancestor of an output package may be a junction into shared Content.
function Stage-Folder([string]$relative) {
    $destination = Join-Path $Run $relative
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    foreach ($folder in Get-ChildItem -LiteralPath (Join-Path $project $relative) -Directory) {
        $child = "$relative/$($folder.Name)"
        if ($packages.Where({$_.StartsWith("$child/")}).Count -gt 0) {
            Stage-Folder $child
        } elseif (!(Test-Path -LiteralPath (Join-Path $Run $child))) {
            New-Item -ItemType Junction -Path (Join-Path $Run $child) -Target $folder.FullName | Out-Null
        }
    }
}
$before = @{}
if ($PublishSaved) {
    # A running editor can hold clean packages open. Resume with the original
    # snapshots after it releases them, without changing the author's baseline.
    $before = Get-Content -LiteralPath "$Run/inputs.json" -Raw | ConvertFrom-Json -AsHashtable
} else {
    foreach ($rel in $packages + $sourceFiles) {
        $before[$rel] = (Get-FileHash -LiteralPath (Join-Path $project $rel)).Hash
    }
    $before | ConvertTo-Json | Set-Content -LiteralPath "$Run/inputs.json" -Encoding utf8
    Stage-Folder 'Content'
    foreach ($rel in $packages) {
        Copy-Item -LiteralPath (Join-Path $project $rel) -Destination (Join-Path $Run $rel)
    }
    @{FileVersion=3;EngineAssociation='5.8';Plugins=@(
        @{Name='GeometryScripting';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true},@{Name='PythonScriptPlugin';Enabled=$true}
    )} | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 "$Run/Battlements.uproject"
    @('[ConsoleVariables]','r.VirtualTextures=1','r.AllowStaticLighting=0') | Set-Content "$Run/Config/DefaultEngine.ini"
    $cmd = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $arguments = @(('"' + $Run + '/Battlements.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',
        ('-script="' + $PSScriptRoot + '/build_battlement_assets.py"'),'-NullRHI','-nosound','-nosplash','-nop4','-unattended',
        '-Multiprocess','-NoAssetRegistryCacheWrite','-AssetGatherAll=false','-ini:Engine:[SystemSettings]:Editor.AsyncStaticMeshCompilation=0',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorExperimentalSettings]:bEnableAsyncStaticMeshCompilation=False',
        '-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache','-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen',
        '-ini:Engine:[VirtualTextureChunkDDCCache]:Path=F:/FPSGAMEData/Caches/DerivedDataCache/VT',
        ('-abslog="' + $Run + '/engine.log"'))
    $proc = Start-Process -FilePath $cmd -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
    if ($proc.ExitCode -ne 0 -or !(Test-Path -LiteralPath "$Run/saved.json")) {
        Select-String -LiteralPath "$Run/engine.log" -Pattern 'LogPython: Error|Fatal error' | Select-Object -Last 12
        throw "Wall package build incomplete at $Run"
    }
}
$result = Get-Content -LiteralPath "$Run/saved.json" -Raw | ConvertFrom-Json
$pieces = foreach ($row in ($result.meshes | Select-Object -Skip 1)) {
    @{mesh=$row.stages[0].path;triangles=$row.raw_triangles;intact_source_sha256=$result.source_sha256;
      lod_triangles=$row.stages[0].lod_triangles}
}
$pieces | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$Run/Authored/fracture-saved.json" -Encoding utf8
$mutex = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try {$held=$mutex.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    foreach ($rel in $before.Keys) {
        if ((Get-FileHash -LiteralPath (Join-Path $project $rel)).Hash -ne $before[$rel]) {
            throw "Another edit changed $rel during authoring. Outputs remain in $Run"
        }
    }
    # The other roles share this index. Merge only the intact wall entry under the bridge lock.
    $index = Get-Content -LiteralPath "$project/$design/imported.json" -Raw | ConvertFrom-Json
    $wall = $result.meshes[0]
    $index.saved.SM_HighWall = @{path=$wall.stages[0].path;materials=$result.materials;triangles=$wall.raw_triangles;
        collision_boxes=$result.boxes.Count;source_sha256=$result.source_sha256}
    $index | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$Run/Authored/imported.json" -Encoding utf8
    $targets = $packages + $sourceFiles + "$design/imported.json"
    $published = @()
    foreach ($rel in $targets) {
        $source = if ($packages -contains $rel) { Join-Path $Run $rel } else { Join-Path "$Run/Authored" (Split-Path $rel -Leaf) }
        $target = Join-Path $project $rel
        $backup = Join-Path "$Run/Previous" $rel
        New-Item -ItemType Directory -Path (Split-Path $backup -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $target -Destination $backup
        Copy-Item -LiteralPath $source -Destination "$target.$PID.pending"
    }
    try {
        foreach ($rel in $targets) {
            $target = Join-Path $project $rel
            [IO.File]::Move("$target.$PID.pending", $target, $true)
            $published += $rel
        }
    } catch {
        foreach ($rel in $published) {
            $target = Join-Path $project $rel
            Copy-Item -LiteralPath (Join-Path "$Run/Previous" $rel) -Destination "$target.$PID.restore"
            [IO.File]::Move("$target.$PID.restore", $target, $true)
        }
        throw
    } finally {
        foreach ($rel in $targets) {
            $pending = (Join-Path $project $rel) + ".$PID.pending"
            if (Test-Path -LiteralPath $pending) {Remove-Item -LiteralPath $pending}
        }
    }
    Copy-Item -LiteralPath "$Run/saved.json" -Destination "$Run/published.json"
} finally {
    if ($held) {$mutex.ReleaseMutex()}
    $mutex.Dispose()
}
Write-Output "$Run/published.json"
