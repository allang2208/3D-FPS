$ErrorActionPreference='Stop'
foreach ($blizzardVersion in @('StormV2','RollingV1')) {
    & (Join-Path $PSScriptRoot 'run_blizzard_visual_capture_20261115.ps1') -SkipBuild -ReadOnlyCapture -Stage ('VersionComparison/'+$blizzardVersion) -CloudVersion $blizzardVersion
}
