<#
Generate ui/palette.json from ui/style.gd color constants.
Also prints the _apply_colors() body (static var overrides) for pasting into style.gd.

Usage: powershell -File tools/gen-palette.ps1 [-ProjectDir E:\3d\3-dfps]
#>
param([string]$ProjectDir = 'E:\3d\3-dfps')

$ErrorActionPreference = 'Stop'
$stylePath = Join-Path $ProjectDir 'ui\style.gd'
$jsonPath = Join-Path $ProjectDir 'ui\palette.json'

if (-not (Test-Path $stylePath)) { Write-Error "style.gd not found: $stylePath" }
$text = [System.IO.File]::ReadAllText($stylePath)

function To-Hex([double]$r, [double]$g, [double]$b, [double]$a) {
  $hr = '{0:X2}' -f [int][math]::Round($r * 255)
  $hg = '{0:X2}' -f [int][math]::Round($g * 255)
  $hb = '{0:X2}' -f [int][math]::Round($b * 255)
  $hex = "#$hr$hg$hb"
  if ($a -lt 0.999) { $hex += '{0:X2}' -f [int][math]::Round($a * 255) }
  return $hex
}

function Get-ColorConsts([string]$src) {
  $out = @{}
  $rx = [regex]'static var (COLOR_\w+|THEME_\w+): Color = Color\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)(?:\s*,\s*([0-9.]+))?\s*\)'
  foreach ($m in $rx.Matches($src)) {
    $a = 1.0
    if ($m.Groups[5].Success) { $a = [double]$m.Groups[5].Value }
    $out[$m.Groups[1].Value] = To-Hex ([double]$m.Groups[2].Value) ([double]$m.Groups[3].Value) ([double]$m.Groups[4].Value) $a
  }
  return $out
}

function Get-DictColors([string]$src, [string]$dictName) {
  $out = @{}
  $block = [regex]::Match($src, "static var ${dictName}: Dictionary = \{([^}]*)\}")
  if (-not $block.Success) { return $out }
  $rowRx = [regex]'"(\w+)":\s*Color\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)(?:\s*,\s*([0-9.]+))?\s*\)'
  foreach ($m in $rowRx.Matches($block.Groups[1].Value)) {
    $a = 1.0
    if ($m.Groups[5].Success) { $a = [double]$m.Groups[5].Value }
    $out[$m.Groups[1].Value] = To-Hex ([double]$m.Groups[2].Value) ([double]$m.Groups[3].Value) ([double]$m.Groups[4].Value) $a
  }
  return $out
}

$colors = Get-ColorConsts $text
$rarity = Get-DictColors $text 'RARITY_COLORS'
$badge = Get-DictColors $text 'RARITY_BADGE_COLORS'

$colorsObj = [ordered]@{}
$colors.GetEnumerator() | Sort-Object Name | ForEach-Object { $colorsObj[$_.Key] = $_.Value }
$payload = [ordered]@{
  version = 1
  colors = $colorsObj
  rarity_colors = $rarity
  rarity_badge_colors = $badge
}
$json = $payload | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText($jsonPath, $json, [System.Text.UTF8Encoding]::new($false))

Write-Host "palette.json written: $jsonPath ($($colors.Count) colors, $($rarity.Count) rarity, $($badge.Count) badges)"

Write-Host "`n--- _apply_colors() body (paste into ui/style.gd) ---"
$sorted = $colors.Keys | Sort-Object
foreach ($k in $sorted) {
  Write-Host "`tif p.has(`"$k`"): $k = _hex_to_color(p.$k)"
}
Write-Host "`tvar rc: Dictionary = p.get(`"rarity_colors`", {})"
Write-Host "`tfor key in rc:"
Write-Host "`t`tif RARITY_COLORS.has(key): RARITY_COLORS[key] = _hex_to_color(rc[key])"
Write-Host "`tvar rbc: Dictionary = p.get(`"rarity_badge_colors`", {})"
Write-Host "`tfor key in rbc:"
Write-Host "`t`tif RARITY_BADGE_COLORS.has(key): RARITY_BADGE_COLORS[key] = _hex_to_color(rbc[key])"
