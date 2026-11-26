param([string]$Work='F:/FPSGAMEData/ArtProduction/VillageStoneRelief/Binding',[string]$GeometryRun='')
$ErrorActionPreference='Stop'
$project=(Resolve-Path -LiteralPath "$PSScriptRoot/../../..").Path
$hills='WorldGeneration/TemperateHills'
$masonry="$hills/VillageMasonry"
$source="$project/Content/$masonry"
$names=@('SM_Bakery_AbandonedHouseMasonry','SM_ChapelYardPier','SM_ChapelYardWallA','SM_ChapelYardWallB',
    'SM_HighPortalGalleryEast','SM_HighPortalGalleryWest','SM_HighWall','SM_StoneChunkA','SM_StoneChunkB')
foreach ($variant in 'PierRepaired','PierRuined','RepairedA','RepairedB','RubbleA','RubbleB','RuinedA','RuinedB','RuinedC','RuinedD') {
    $names+="SM_VillageWall$variant"
}
foreach ($index in 0..8) {$names+=('SM_HighWallShard_{0:00}' -f $index)}
$surfaceNames='MI_Main_StoneWall_00A','MI_Main_StoneWall_00B_Gray','MI_StoneWall_Pieces_00A','MI_Main_Mortar_00A'
foreach ($name in $surfaceNames) {
    if (!(Test-Path -LiteralPath "$source/Relief/$name.uasset")) {throw "Waiting for the authored relief material $name"}
}
$run=Join-Path $Work (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
$content="$run/Content"
$dst="$content/$masonry/ReliefMeshes"
New-Item -ItemType Directory -Force -Path $dst,"$run/Config" | Out-Null
$srcLevel="$project/Content"
$dstLevel=$content
foreach ($branch in 'WorldGeneration','TemperateHills','VillageMasonry','ReliefMeshes'){
    foreach ($folder in Get-ChildItem -LiteralPath $srcLevel -Directory) {
        if ($folder.Name -ne $branch) {
            New-Item -ItemType Junction -Path (Join-Path $dstLevel $folder.Name) -Target $folder.FullName | Out-Null
        }
    }
    # Some collision or material packages sit at the same depth as these folders.
    Get-ChildItem -LiteralPath $srcLevel -File -Filter '*.uasset' | Copy-Item -Destination $dstLevel
    $srcLevel=Join-Path $srcLevel $branch
    $dstLevel=Join-Path $dstLevel $branch
}
$snapshots=@{}
$readLevel=if ($GeometryRun) {Join-Path $GeometryRun "Content/$masonry/ReliefMeshes"} else {$srcLevel}
if ($GeometryRun -and !(Test-Path -LiteralPath (Join-Path $GeometryRun 'saved.json'))) {
    throw "Displaced geometry authoring is still in progress at $GeometryRun"
}
foreach ($name in $names) {
    if (!(Test-Path -LiteralPath "$readLevel/$name.uasset")) {throw "Missing authored relief mesh $name"}
    Get-ChildItem -LiteralPath $readLevel -File -Filter "$name.*" | ForEach-Object {
        if ($_.Extension -in '.uasset','.ubulk','.uexp','.uptnl') {
            Copy-Item -LiteralPath $_.FullName -Destination $dst
            $snapshots[$_.Name]=(Get-FileHash -LiteralPath "$dst/$($_.Name)").Hash
        }
    }
}
$names | ConvertTo-Json | Set-Content -Encoding utf8 "$run/inputs.json"
@{FileVersion=3; EngineAssociation='5.8'; Plugins=@(@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})} |
    ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 "$run/Binding.uproject"
@('[ConsoleVariables]','r.VirtualTextures=1','r.AllowStaticLighting=0') | Set-Content "$run/Config/DefaultEngine.ini"
$env:STONE_RELIEF_BIND_WORK=$run
$params=@(('"'+$run+'/Binding.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',
    ('-script="'+$PSScriptRoot+'/bind_stone_relief.py"'),'-unattended','-NullRHI','-nosplash','-nosound','-nop4',
    '-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite','-ini:Engine:[SystemSettings]:Editor.AsyncStaticMeshCompilation=0',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorExperimentalSettings]:bEnableAsyncStaticMeshCompilation=False',
    '-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache','-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen',
    '-ini:Engine:[VirtualTextureChunkDDCCache]:Path=F:/FPSGAMEData/Caches/DerivedDataCache/VT',
    ('-abslog="'+$run+'/engine.log"'))
$proc=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $params -Wait -PassThru -WindowStyle Hidden
if ($proc.ExitCode -ne 0 -or !(Test-Path -LiteralPath "$run/bindings.json")) {
    Select-String -Path "$run/engine.log" -Pattern 'LogPython: Error|Fatal error' | Select-Object -Last 12
    throw "Material slot binding failed. $run"
}
$rows=Get-Content -Raw -LiteralPath "$run/bindings.json" | ConvertFrom-Json
if ($GeometryRun) {
    # Work on the immutable authoring result while the geometry writer waits for
    # the editor gate. Publish only after its input packages reach this project.
    while (@($names | Where-Object {!(Test-Path -LiteralPath "$srcLevel/$_.uasset")}).Count) {Start-Sleep -Seconds 4}
}
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$mutex.WaitOne()}catch [Threading.AbandonedMutexException] {$held=$true}
    $publish=@()
    foreach ($row in $rows) {
        if (!$row.changed) {continue}
        $name=($row.mesh -split '/')[-1]
        # Save any updated bulk payload before switching its package header.
        foreach ($ext in '.ubulk','.uexp','.uptnl','.uasset') {
            $entry=$name+$ext
            if (!(Test-Path -LiteralPath "$dst/$entry")) {continue}
            $current=if(Test-Path -LiteralPath "$srcLevel/$entry"){(Get-FileHash -LiteralPath "$srcLevel/$entry").Hash}else{$null}
            if ($current -ne $snapshots[$entry]) {throw "Geometry package changed during binding: $entry"}
            if ($current -ne (Get-FileHash -LiteralPath "$dst/$entry").Hash) {$publish+=$entry}
        }
    }
    foreach($entry in $publish){
        $file=Join-Path $srcLevel $entry
        $pending="$file.$PID.tmp"
        Copy-Item -LiteralPath "$dst/$entry" -Destination $pending
        [IO.File]::Move($pending,$file,$true)
    }
    Copy-Item -LiteralPath "$run/bindings.json" -Destination "$run/published.json"
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
Write-Output "Published village relief bindings: $run/published.json"
