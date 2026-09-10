$ErrorActionPreference = 'Stop'
$rainRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$rainContent = Join-Path $rainRoot 'Content/Weather/VFX'
$rainBackup = Join-Path $rainRoot 'trash/weather-upgrade-20260910/backup'
$rainTrash = Join-Path $rainRoot 'trash/weather-upgrade-20260910/retired-assets'
New-Item -ItemType Directory -Force -Path $rainTrash | Out-Null
$rainReport = @()
# Exact retired files only. Archive recoverably; never close editors or remove shared packs.
foreach ($rainName in @('NS_FPS_Rain.uasset', 'NS_FPS_RainSplashes.uasset')) {
    $rainFile = Join-Path $rainContent $rainName
    $rainCopy = Join-Path $rainBackup $rainName
    $rainState = 'already_absent'
    if (Test-Path -LiteralPath $rainFile) {
        if (!(Test-Path -LiteralPath $rainCopy) -or
            (Get-FileHash -LiteralPath $rainFile).Hash -ne (Get-FileHash -LiteralPath $rainCopy).Hash) {
            throw "Backup does not match retired file: $rainName"
        }
        $rainDestination = Join-Path $rainTrash $rainName
        $rainResolved = (Resolve-Path -LiteralPath $rainFile).Path
        if ([IO.Path]::GetDirectoryName($rainResolved) -ne (Resolve-Path -LiteralPath $rainContent).Path) {
            throw "Unexpected retirement source: $rainResolved"
        }
        if (Test-Path -LiteralPath $rainDestination) { throw "Archive already exists: $rainDestination" }
        try { Move-Item -LiteralPath $rainResolved -Destination $rainDestination -ErrorAction Stop; $rainState = 'archived' }
        catch { $rainState = 'locked_or_unavailable'; Write-Warning "$rainName remains on disk: $($_.Exception.Message)" }
    }
    $rainReport += [pscustomobject]@{name=$rainName; status=$rainState; original=$rainFile; destination=(Join-Path $rainTrash $rainName); bytes=if(Test-Path -LiteralPath $rainCopy){(Get-Item -LiteralPath $rainCopy).Length}else{0}; sha256=if(Test-Path -LiteralPath $rainCopy){(Get-FileHash -LiteralPath $rainCopy).Hash}else{$null}}
}
$rainReport | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $rainRoot 'Saved/RainUpgrade/retirement.json')
$rainReport
