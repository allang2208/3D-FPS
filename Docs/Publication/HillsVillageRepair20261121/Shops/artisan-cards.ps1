param(
    [Parameter(Mandatory)][string]$SourceDirectory,
    [Parameter(Mandatory)][string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationCore,WindowsBase,PresentationFramework
$manifest = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'construction-cards.json') | ConvertFrom-Json
$targetFolder = [IO.Directory]::CreateDirectory($OutputDirectory)

foreach ($role in 'blacksmith', 'carpenter') {
    $sourcePath = (Resolve-Path -LiteralPath (Join-Path $SourceDirectory $manifest.cards.$role.image_source)).Path
    $bitmap = [Windows.Media.Imaging.BitmapFrame]::Create(
        [Uri]::new($sourcePath), [Windows.Media.Imaging.BitmapCreateOptions]::PreservePixelFormat,
        [Windows.Media.Imaging.BitmapCacheOption]::OnLoad)
    $visual = [Windows.Media.DrawingVisual]::new()
    [Windows.Media.RenderOptions]::SetBitmapScalingMode($visual, [Windows.Media.BitmapScalingMode]::Fant)
    $scale = 244.0 / [Math]::Max($bitmap.PixelWidth, $bitmap.PixelHeight)
    $width = $bitmap.PixelWidth * $scale
    $height = $bitmap.PixelHeight * $scale
    $drawing = $visual.RenderOpen()
    $drawing.DrawImage($bitmap, [Windows.Rect]::new((256 - $width) / 2, (256 - $height) / 2, $width, $height))
    $drawing.Close()

    $tile = [Windows.Media.Imaging.RenderTargetBitmap]::new(256, 256, 96, 96, [Windows.Media.PixelFormats]::Pbgra32)
    $tile.Render($visual)
    $encoder = [Windows.Media.Imaging.PngBitmapEncoder]::new()
    $encoder.Frames.Add([Windows.Media.Imaging.BitmapFrame]::Create($tile))
    $stream = [IO.File]::Create((Join-Path $targetFolder.FullName ($role + '.png')))
    try { $encoder.Save($stream) } finally { $stream.Dispose() }
}
