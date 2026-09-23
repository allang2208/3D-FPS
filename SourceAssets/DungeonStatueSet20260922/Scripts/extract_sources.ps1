param(
    [string[]]$Keys
)
# Unpacks every downloaded source archive into Source/<key>/ and extracts one level of
# nested archives (the author ships "source/<name>.zip" plus "textures/<atlas>.png").
$ErrorActionPreference = 'Stop'
$case = Split-Path -Parent $PSScriptRoot
$sevenZip = 'C:\Program Files\7-Zip\7z.exe'
$cfg = Get-Content (Join-Path $case 'Config\statues.json') -Raw -Encoding UTF8 | ConvertFrom-Json

foreach ($s in $cfg.statues) {
    if ($Keys -and ($Keys -notcontains $s.key)) { continue }
    $dlDir = Join-Path $case ('Download\' + $s.key)
    $outDir = Join-Path $case ('Source\' + $s.key)
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    $zip = Get-ChildItem $dlDir -Filter 'source_*.zip' | Select-Object -First 1
    if (-not $zip) { Write-Output "[skip] $($s.key): no source zip"; continue }
    Write-Output "=== $($s.key) : $($zip.Name)"
    & $sevenZip x $zip.FullName "-o$outDir" -y | Select-Object -Last 2
    foreach ($nested in Get-ChildItem $outDir -Recurse -Filter '*.zip') {
        $nestedDir = Join-Path $nested.DirectoryName $nested.BaseName
        New-Item -ItemType Directory -Force -Path $nestedDir | Out-Null
        Write-Output "  [nested] $($nested.Name)"
        & $sevenZip x $nested.FullName "-o$nestedDir" -y | Select-Object -Last 2
    }
}

Write-Output ''
Write-Output '=== inventory ==='
foreach ($s in $cfg.statues) {
    $dir = Join-Path $case ('Source\' + $s.key)
    if (-not (Test-Path $dir)) { continue }
    Write-Output "--- $($s.key)"
    Get-ChildItem $dir -Recurse -File | Sort-Object Length -Descending |
        Select-Object -First 8 @{n = 'MB'; e = { [math]::Round($_.Length / 1MB, 1) } }, @{n = 'rel'; e = { $_.FullName.Replace($dir, '') } } |
        Format-Table -AutoSize | Out-String -Width 140
}
