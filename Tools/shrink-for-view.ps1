<#
.SYNOPSIS
  Make a small reading copy of a big review sheet before viewing it in the chat.

.DESCRIPTION
  The local deepseek-v4-flash channel now accepts native image input, so every image read
  by view_image stays in the session as base64 and the whole history is resent on every
  turn. Four or five 1-4 MB review sheets are fine; about 50 MB of them is not: the request
  body crosses the upstream buffer limit and the turn fails with

    413 Payload Too Large: Failed to buffer the request body: length limit exceeded

  after which every further message on that thread fails too, because each one resends the
  same oversized body.

  This script writes downscaled JPEG copies (default long edge 1400, quality 80, usually
  150-400 KB) next to the originals, so the chat can look at them. The copies are for
  reading only: pixel measurement, alpha edge fitting and IoU checks must keep reading the
  original PNG.

.PARAMETER Image
  One or more local image paths, absolute or relative to the current directory.

.PARAMETER MaxLong
  Long edge of the copy in pixels. Default 1400.

.PARAMETER Quality
  JPEG quality 1-100. Default 80.

.PARAMETER OutDir
  Output directory. Default: '<folder of the first image>/View'.

.PARAMETER Force
  Rewrite copies whose timestamp is older than the source.

.EXAMPLE
  & Tools/shrink-for-view.ps1 'SourceAssets/RuneSword20260913/ChargedErgoV43/ReviewV45/sheet_fp.png'

.EXAMPLE
  & Tools/shrink-for-view.ps1 (Get-ChildItem 'SourceAssets/RuneSword20260913/ChargedErgoV43/ReviewV45/sheet_*.png').FullName
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string[]]$Image,

    [int]$MaxLong = 1400,
    [int]$Quality = 80,
    [string]$OutDir,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$jpegCodec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() |
    Where-Object { $_.MimeType -eq 'image/jpeg' } | Select-Object -First 1
if (-not $jpegCodec) { throw 'No JPEG encoder available in System.Drawing.' }

$encoderParams = New-Object -TypeName System.Drawing.Imaging.EncoderParameters -ArgumentList @(1)
$encoderParams.Param[0] = New-Object -TypeName System.Drawing.Imaging.EncoderParameter `
    -ArgumentList @([System.Drawing.Imaging.Encoder]::Quality, [int64]$Quality)

$sources = foreach ($raw in $Image) {
    $p = if ([System.IO.Path]::IsPathRooted($raw)) { $raw } else { Join-Path (Get-Location).Path $raw }
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { throw "Image not found: $p" }
    (Get-Item -LiteralPath $p).FullName
}

if (-not $OutDir) { $OutDir = Join-Path (Split-Path -Parent $sources[0]) 'View' }
if (-not (Test-Path -LiteralPath $OutDir)) { $null = New-Item -ItemType Directory -Path $OutDir }
$OutDir = (Get-Item -LiteralPath $OutDir).FullName

$rows = New-Object System.Collections.Generic.List[object]
$total = 0L

foreach ($src in $sources) {
    $name = [System.IO.Path]::GetFileNameWithoutExtension($src)
    $dst = Join-Path $OutDir ($name + '.jpg')
    $srcItem = Get-Item -LiteralPath $src
    $srcBytes = $srcItem.Length

    $skip = (-not $Force) -and (Test-Path -LiteralPath $dst) -and
            ((Get-Item -LiteralPath $dst).LastWriteTimeUtc -ge $srcItem.LastWriteTimeUtc)

    if (-not $skip) {
        $img = [System.Drawing.Image]::FromFile($src)
        try {
            $long = [Math]::Max($img.Width, $img.Height)
            $scale = [Math]::Min(1.0, $MaxLong / [double]$long)
            $w = [int][Math]::Round($img.Width * $scale)
            $h = [int][Math]::Round($img.Height * $scale)
            $bmp = New-Object -TypeName System.Drawing.Bitmap -ArgumentList @($w, $h)
            try {
                $g = [System.Drawing.Graphics]::FromImage($bmp)
                try {
                    $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
                    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
                    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
                    $g.DrawImage($img, 0, 0, $w, $h)
                } finally { $g.Dispose() }
                $bmp.Save($dst, $jpegCodec, $encoderParams)
            } finally { $bmp.Dispose() }
        } finally { $img.Dispose() }
    }

    $dstBytes = (Get-Item -LiteralPath $dst).Length
    $total += $dstBytes
    $rows.Add([pscustomobject]@{
        Copy      = $dst
        SourceMB  = [Math]::Round($srcBytes / 1MB, 2)
        CopyKB    = [Math]::Round($dstBytes / 1KB, 0)
        Reused    = $skip
    })
}

$rows | Format-Table Copy, SourceMB, CopyKB, Reused -AutoSize

"{0} copies, {1:N0} KB total ({2:N2} MB) -> {3}" -f $rows.Count, ($total / 1KB), ($total / 1MB), $OutDir
"Budget reminder: keep the sum of inlined images per thread under about 10 MB and open a new thread per version."
