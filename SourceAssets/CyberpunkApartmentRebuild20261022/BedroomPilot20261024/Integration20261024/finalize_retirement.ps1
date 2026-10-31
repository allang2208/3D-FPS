param([int]$QueueWaitSeconds=900)
$ErrorActionPreference='Stop'
$bedroomProject=[IO.Path]::GetFullPath('D:\FPS3D\FPSGAME')
$bedroomContent=Join-Path $bedroomProject 'Content'
$bedroomArchive=Join-Path $bedroomProject 'trash\cyberpunk-bedroom-pilot-retired-20261024'
$bedroomGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$bedroomHeld=$false
try {
    $bedroomHeld=$bedroomGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))
    if(-not $bedroomHeld){throw 'UE publication window busy; no files changed.'}
    if(Get-Process -Name UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An Unreal process is still running; preserve loaded packages.'}
    $bedroomInstalled=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'installed.json') | ConvertFrom-Json
    if($bedroomInstalled.stage -ne 'formal_apartment_saved'){throw 'Formal apartment must be saved first.'}
    $bedroomRows=@()
    foreach($bedroomName in @('L_CyberpunkBedroom_Pilot20261024.umap','L_CyberpunkBedroom_Pilot20261024.uexp','L_CyberpunkBedroom_Pilot20261024.ubulk','L_CyberpunkBedroom_Pilot20261024_BuiltData.uasset','L_CyberpunkBedroom_Pilot20261024_BuiltData.uexp','L_CyberpunkBedroom_Pilot20261024_BuiltData.ubulk')) {
        $bedroomRelative=Join-Path 'Content\GameMaps\Design' $bedroomName
        $bedroomSource=[IO.Path]::GetFullPath((Join-Path $bedroomProject $bedroomRelative))
        $bedroomDestination=[IO.Path]::GetFullPath((Join-Path $bedroomArchive $bedroomRelative))
        if(-not $bedroomSource.StartsWith($bedroomContent+'\',[StringComparison]::OrdinalIgnoreCase) -or -not $bedroomDestination.StartsWith($bedroomArchive+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Retirement path outside approved directories.'}
        if(-not (Test-Path -LiteralPath $bedroomSource -PathType Leaf)){continue}
        $bedroomInfo=Get-Item -LiteralPath $bedroomSource
        $bedroomHash=(Get-FileHash -LiteralPath $bedroomSource -Algorithm SHA256).Hash.ToLowerInvariant()
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $bedroomDestination) | Out-Null
        if(-not (Test-Path -LiteralPath $bedroomDestination)){Copy-Item -LiteralPath $bedroomSource -Destination $bedroomDestination}
        if((Get-FileHash -LiteralPath $bedroomDestination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $bedroomHash){throw 'Archive differs from the exact file to retire.'}
        Remove-Item -LiteralPath $bedroomSource
        $bedroomRows+=@{original=$bedroomSource;archive=$bedroomDestination;size=$bedroomInfo.Length;sha256=$bedroomHash;reason='Bedroom V3 integrated into the existing apartment; independent sample retired';replacement='/Game/GameMaps/L_CyberpunkApartment'}
    }
    $bedroomReport=@{stage='sample_map_retired';formal_map='/Game/GameMaps/L_CyberpunkApartment';retired_map='/Game/GameMaps/Design/L_CyberpunkBedroom_Pilot20261024';retired_at=(Get-Date).ToString('o');files=$bedroomRows;game_run=$false;method='UE asset deletion followed by exact-file removal after its commandlet exited'}
    $bedroomText=$bedroomReport | ConvertTo-Json -Depth 8
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'retired.json'),$bedroomText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $bedroomArchive 'manifest.json'),$bedroomText,[Text.UTF8Encoding]::new($false))
    Write-Output ('BEDROOM_SAMPLE_FILES_RETIRED '+$bedroomRows.Count)
} finally {
    if($bedroomHeld){$bedroomGate.ReleaseMutex()}
    $bedroomGate.Dispose()
}
