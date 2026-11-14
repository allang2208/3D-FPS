$ErrorActionPreference='Stop'
$project='D:\FPS3D\FPSGAME'
$sourceHash='4E617234A3567F83CD315C60E7F3BC2E61CD1FA43C96F1DE4A347316339A4B11'
$rel='Content/GameMaps/Design/L_FreightTransit_Theme_Subject.umap'
$dst=Join-Path $project $rel
$src=Join-Path (Join-Path $PSScriptRoot 'RenderHost') $rel
if(!(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'done-11.json'))){throw 'Private map not saved'}
$photoHash=(Get-FileHash -LiteralPath $src).Hash
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$mutex.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    if((Test-Path -LiteralPath (Join-Path $PSScriptRoot 'published.json')) -and (Get-FileHash -LiteralPath $dst).Hash -eq $photoHash){return}
    $procs=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'UnrealEditor*' -and ($_.CommandLine -match 'D:[/\\]FPS3D[/\\]FPSGAME[/\\]FPSGAME\.uproject' -or -not $_.CommandLine) -and !($_.Name -eq 'UnrealEditor-Cmd.exe' -and ($_.CommandLine -match '(?i)\s-run=ColdSteelDungeonFogCheck\s' -or $_.CommandLine -match '(?i)\s-script=D:[/\\]FPS3D[/\\]FPSGAME[/\\]Saved[/\\]BoarAppearance[/\\]author_grey\.py\s'))})
    if($procs.Count){throw 'The production project has an active editor process'}
    if((Get-FileHash -LiteralPath $dst).Hash -ne $sourceHash){throw 'Original map changed'}
    $backup=Join-Path $PSScriptRoot 'prior-map.umap'
    $temp=$dst+'.cartbay.tmp'
    [IO.File]::Copy($src,$temp,$true)
    if((Get-FileHash -LiteralPath $temp).Hash -ne $photoHash){throw 'Incomplete package copy'}
    [IO.File]::Replace($temp,$dst,$backup,$true)
    if((Get-FileHash -LiteralPath $dst).Hash -ne $photoHash -or (Get-FileHash -LiteralPath $backup).Hash -ne $sourceHash){throw 'Publication mismatch'}
    @{map='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject';original=$sourceHash;saved=$photoHash;comparison='CartBay-UpperWall-Comparison.jpg';view='REF_02_CartSurface'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'published.json') -Encoding UTF8
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
