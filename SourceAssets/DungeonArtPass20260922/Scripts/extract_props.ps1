param([string]$Keys = '')
# Unpacks each prop's source archive into Source/<key>/ and one level of nested archives.
$ErrorActionPreference = 'Stop'
$case = Split-Path -Parent $PSScriptRoot
$sevenZip = 'C:\Program Files\7-Zip\7z.exe'
$cfg = Get-Content (Join-Path $case 'Config\props.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$dlRoot = 'D:\FPS3D\_sketchfab_goddess\artpass\download'
$only = @()
if ($Keys) { $only = $Keys.Split(',') }

foreach ($p in $cfg.props) {
    if ($only.Count -and ($only -notcontains $p.key)) { continue }
    $dlDir = Join-Path $dlRoot $p.key
    $outDir = Join-Path $case ('Source\' + $p.key)
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    $zip = Get-ChildItem $dlDir -Filter 'source_*.zip' -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $zip) { Write-Output "[skip] $($p.key): no source zip"; continue }
    Write-Output "=== $($p.key) : $($zip.Name)"
    & $sevenZip x $zip.FullName "-o$outDir" -y | Select-Object -Last 1
    foreach ($nested in Get-ChildItem $outDir -Recurse -Filter '*.zip') {
        $nestedDir = Join-Path $nested.DirectoryName $nested.BaseName
        New-Item -ItemType Directory -Force -Path $nestedDir | Out-Null
        Write-Output "  [nested] $($nested.Name)"
        & $sevenZip x $nested.FullName "-o$nestedDir" -y | Select-Object -Last 1
    }
}

Write-Output ''
Write-Output '=== inventory (mesh + texture candidates) ==='
foreach ($p in $cfg.props) {
    if ($only.Count -and ($only -notcontains $p.key)) { continue }
    $dir = Join-Path $case ('Source\' + $p.key)
    if (-not (Test-Path $dir)) { continue }
    Write-Output "--- $($p.key)"
    Get-ChildItem $dir -Recurse -File |
        Where-Object { $_.Extension -in '.obj', '.fbx', '.gltf', '.glb', '.png', '.jpg', '.jpeg', '.tga', '.mtl', '.blend' } |
        Sort-Object Length -Descending |
        Select-Object -First 12 @{n = 'MB'; e = { [math]::Round($_.Length / 1MB, 2) } }, @{n = 'rel'; e = { $_.FullName.Replace($dir, '') } } |
        Format-Table -AutoSize | Out-String -Width 150
}
