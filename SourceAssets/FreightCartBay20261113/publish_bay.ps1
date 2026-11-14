$ErrorActionPreference='Stop'
$project='D:\FPS3D\FPSGAME'
$sourceHash='05F9FCAB6487B74B101C765DFB59E7C2F3E1F28A5E97CC1146FF54714AECE3DF'
$rel='Content/GameMaps/Design/L_FreightTransit_Theme_Subject.umap'
$dst=Join-Path $project $rel
$src=Join-Path (Join-Path $PSScriptRoot 'RenderHost') $rel
if(!(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'done-14.json'))){throw 'Private map not saved'}
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
    @{map='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject';original=$sourceHash;saved=$photoHash;comparison='CartBay-Reference-UE.jpg';view='REF_02_CartSurface'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'published.json') -Encoding UTF8
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
