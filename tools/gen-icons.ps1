<#
Extract Lucide icons (from local shadcn-ui repo node_modules) into assets/ui/icons as SVG.
Usage: powershell -File tools/gen-icons.ps1 [-IconsDir ...] [-OutDir ...]
SVG size: 96x96 (viewBox 24) so Godot imports a crisp texture at any HUD scale.
#>
param(
  [string]$IconsDir = 'E:\3d\shadcn-ui\apps\v4\node_modules\lucide-react\dist\esm\icons',
  [string]$OutDir = 'E:\3d\3-dfps\assets\ui\icons'
)

$ErrorActionPreference = 'Stop'
$names = @(
  'heart','shield','sword','crosshair','zap','waves','coins','gem','backpack','package',
  'settings','volume-2','volume-x','pause','play','power','search','x','check',
  'chevron-down','chevron-left','chevron-right','plus','trash-2','map','flag','trophy','skull',
  'key','lock','eye','info','menu','refresh-cw','sparkles','flame','target',
  'save','pencil-line','activity','timer','star','user','footprints','hard-hat','radio','circle-dollar-sign',
  'triangle-alert'
)

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }

$svgHead = '<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'

function Get-SvgNodes([string]$blockText) {
  $out = @()
  $nodeRx = [regex]'\[\s*"(\w+)",\s*\{([\s\S]*?)\}\s*\]'
  foreach ($m in $nodeRx.Matches($blockText)) {
    $tag = $m.Groups[1].Value
    $attrs = @{}
    foreach ($am in [regex]::Matches($m.Groups[2].Value, '(\w+): "([^"]*)"')) {
      if ($am.Groups[1].Value -ne 'key') { $attrs[$am.Groups[1].Value] = $am.Groups[2].Value }
    }
    $attrStr = ($attrs.GetEnumerator() | ForEach-Object { "$($_.Key)=`"$($_.Value)`"" }) -join ' '
    $out += "<$tag $attrStr/>"
  }
  return $out
}

$ok = 0
$missing = @()
foreach ($n in $names) {
  $src = Join-Path $IconsDir ($n + '.js')
  if (-not (Test-Path $src)) { $missing += $n; continue }
  $text = [System.IO.File]::ReadAllText($src)
  $block = [regex]::Match($text, 'const __iconNode = \[([\s\S]*?)\];')
  if (-not $block.Success) { $missing += $n; continue }
  $body = Get-SvgNodes $block.Groups[1].Value
  $svg = $svgHead + ($body -join '') + '</svg>'
  [System.IO.File]::WriteAllText((Join-Path $OutDir ($n + '.svg')), $svg, [System.Text.UTF8Encoding]::new($false))
  $ok++
}

Write-Host "icons written: $ok / $($names.Count)"
if ($missing.Count -gt 0) { Write-Host ('missing: ' + ($missing -join ', ')) }
