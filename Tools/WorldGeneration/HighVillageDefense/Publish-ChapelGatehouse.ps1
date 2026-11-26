param([string]$Run = (Join-Path 'F:/FPSGAMEData/ArtProduction/HighVillageDefense' (Get-Date -Format 'yyyyMMdd-HHmmss-fff')), [switch]$PortalsOnly, [switch]$HighWallsOnly, [switch]$FramesOnly, [switch]$TowerOnly)
$ErrorActionPreference='Stop'
if($TowerOnly -and ($PortalsOnly -or $HighWallsOnly -or $FramesOnly)){throw "Choose one kit subset"}
$fullKit=!($PortalsOnly -or $FramesOnly -or $HighWallsOnly -or $TowerOnly)
if($FramesOnly -or $TowerOnly){$PortalsOnly=$true}
if($PortalsOnly -and $HighWallsOnly){throw 'Choose one kit subset'}
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$source=Join-Path $project 'SourceAssets/HillsVillageHighWall20261120/ChapelGatehouse'
$rel='Content/WorldGeneration/TemperateHills/HighVillageDefense/ChapelGatehouse'
$live=Join-Path $project $rel
$env:HIGH_VILLAGE_PROJECT=$project
$env:GATEHOUSE_RUN=$Run
New-Item -ItemType Directory -Path "$Run/Config","$Run/$rel" -Force | Out-Null
$before=@{}
if(Test-Path $live){
    foreach($folder in @($live,(Join-Path $live 'SquareKeep'))){
        if(Test-Path -LiteralPath $folder){
            foreach($f in Get-ChildItem -LiteralPath $folder -File -Filter '*.uasset'){
                $key=[IO.Path]::GetRelativePath($live,$f.FullName).Replace('\','/')
                $before[$key]=(Get-FileHash $f.FullName).Hash
            }
        }
    }
}
$env:GATEHOUSE_PORTALS_ONLY=if($PortalsOnly){'1'}else{'0'}
$env:GATEHOUSE_TOWER_ONLY=if($TowerOnly){'1'}else{'0'}
$env:GATEHOUSE_FRAMES_ONLY=if($FramesOnly){'1'}else{'0'}
$env:GATEHOUSE_HIGH_WALLS_ONLY=if($HighWallsOnly){'1'}else{'0'}
if($PortalsOnly -or $HighWallsOnly){
    Copy-Item -LiteralPath "$live/M_GatehouseChapelWall.uasset" -Destination "$Run/$rel/M_GatehouseChapelWall.uasset"
}
if($TowerOnly -or $fullKit){
    py -3.11 "$PSScriptRoot/high_watchtower.py" "$project/SourceAssets/HillsVillageHighWall20261120/HighTower"
    if($LASTEXITCODE){throw "Watchtower mesh export failed"}
}
if(!$HighWallsOnly -and !$TowerOnly){
    py -3.11 "$PSScriptRoot/chapel_gatehouse.py" $source
    if($LASTEXITCODE){throw 'Gatehouse mesh export failed'}
}
if(!$PortalsOnly){
    py -3.11 "$PSScriptRoot/curtain_wall.py" $source
    if($LASTEXITCODE){throw 'Curtain wall mesh export failed'}
}
$src=Join-Path $project 'Content'
$dst=Join-Path $Run 'Content'
foreach($branch in 'WorldGeneration','TemperateHills','HighVillageDefense','ChapelGatehouse'){
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
    ConvertTo-Json -Depth 4 | Set-Content "$Run/Gatehouse.uproject" -Encoding utf8
@('[ConsoleVariables]','r.VirtualTextures=1','r.AllowStaticLighting=0') | Set-Content "$Run/Config/DefaultEngine.ini"
$cmd='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$arguments=@(('"' + $Run + '/Gatehouse.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',('-script="' + $PSScriptRoot + '/import_chapel_gatehouse.py"'),
    '-NullRHI','-nosound','-nosplash','-nop4','-unattended','-Multiprocess','-NoAssetRegistryCacheWrite','-AssetGatherAll=false',
    '-ini:Engine:[SystemSettings]:Editor.AsyncStaticMeshCompilation=0',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorExperimentalSettings]:bEnableAsyncStaticMeshCompilation=False',
    '-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache','-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen',
    '-ini:Engine:[VirtualTextureChunkDDCCache]:Path=F:/FPSGAMEData/Caches/DerivedDataCache/VT',('-abslog="'+$Run+'/author.log"'))
$proc=Start-Process -FilePath $cmd -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
if($proc.ExitCode -ne 0 -or !(Test-Path "$Run/saved.json")){
    Select-String -LiteralPath "$Run/author.log" -Pattern 'LogPython: Error|Fatal error' | Select-Object -Last 12
    throw "Gatehouse import failed at $Run"
}
$receipt=Get-Content "$Run/saved.json" -Raw | ConvertFrom-Json -AsHashtable
$names=@(foreach($entry in $receipt.saved.Values){
    $package=($entry.path -split '\.')[0]
    $base='/Game/WorldGeneration/TemperateHills/HighVillageDefense/ChapelGatehouse/'
    if(!$package.StartsWith($base)){throw "Unexpected saved package: $package"}
    $package.Substring($base.Length)
})
if(!$PortalsOnly -and !$HighWallsOnly){$names+=@('M_GatehouseChapelWall')}
if($receipt.ground_wear){$names+=@('M_DefenseGroundWear')}
$guard=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
$installed=@()
try {
    try{$held=$guard.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    New-Item -ItemType Directory -Path "$live/SquareKeep","$Run/Before/SquareKeep" -Force | Out-Null
    foreach($name in $names){
        $file="$name.uasset"
        $dest=Join-Path $live $file
        $present=Test-Path -LiteralPath $dest
        if($present -ne $before.ContainsKey($file) -or ($present -and (Get-FileHash $dest).Hash -ne $before[$file])){
            throw "Gatehouse package changed during import: $file"
        }
        Copy-Item -LiteralPath "$Run/$rel/$file" -Destination "$dest.$PID.pending"
    }
    foreach($name in $names){
        $file="$name.uasset"
        $dest=Join-Path $live $file
        if($before.ContainsKey($file)){[IO.File]::Replace("$dest.$PID.pending",$dest,"$Run/Before/$file")}
        else{[IO.File]::Move("$dest.$PID.pending",$dest)}
        $installed+=$file
    }
    Copy-Item -LiteralPath "$Run/saved.json" -Destination "$Run/published.json"
} catch {
    foreach($file in $installed){
        $dest=Join-Path $live $file
        if($before.ContainsKey($file)){Copy-Item -LiteralPath "$Run/Before/$file" -Destination $dest -Force}
        else{Remove-Item -LiteralPath $dest}
    }
    throw
} finally {
    foreach($name in $names){
        $tmp=Join-Path $live "$name.uasset.$PID.pending"
        if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp}
    }
    if($held){$guard.ReleaseMutex()}
    $guard.Dispose()
}
Write-Output "$Run/published.json"

