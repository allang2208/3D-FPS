$ErrorActionPreference='Stop'
$r=$PSScriptRoot
$project=(Resolve-Path -LiteralPath (Join-Path $r '../..')).Path
$rel='Content/GameMaps/Design/L_FreightTransit_Theme_Subject.umap'
$dst=Join-Path $project $rel
$src=Join-Path (Join-Path $r 'RenderHost') $rel
$sourceHash='5E956FB08986FFF7BA3498A11216794E1DA723FE18D375288724B1905F8C1E9A'
$backup=Join-Path $r 'prior-map.umap'
$tmp=$dst+'.stationsurface.tmp'
if(!(Test-Path -LiteralPath (Join-Path $r 'done-07.json'))){throw 'Surface layers have not been saved'}
$mx=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$locked=$false
try {
    try {$locked=$mx.WaitOne()} catch [Threading.AbandonedMutexException] {$locked=$true}
    $srcHash=(Get-FileHash -LiteralPath $src).Hash
    if((Test-Path -LiteralPath (Join-Path $r 'published.json')) -and (Get-FileHash -LiteralPath $dst).Hash -eq $srcHash){return}
    $targetProcesses=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'UnrealEditor*' -and ($_.CommandLine -match 'D:[/\\]FPS3D[/\\]FPSGAME[/\\]FPSGAME\.uproject' -or !$_.CommandLine)})
    if($targetProcesses.Count){throw 'Production editor active; publish using the existing editor bridge'}
    if((Get-FileHash -LiteralPath $dst).Hash -ne $sourceHash){throw 'Current map has concurrent edits'}
    if(!(Test-Path -LiteralPath $backup)){[IO.File]::Copy($dst,$backup,$false)}
    if((Get-FileHash -LiteralPath $backup).Hash -ne $sourceHash){throw 'Backup differs from the original level'}
    [IO.File]::Copy($src,$tmp,$true)
    if((Get-FileHash -LiteralPath $tmp).Hash -ne $srcHash){throw 'Incomplete saved package'}
    [IO.File]::Move($tmp,$dst,$true)
    if((Get-FileHash -LiteralPath $dst).Hash -ne $srcHash -or (Get-FileHash -LiteralPath $backup).Hash -ne $sourceHash){throw 'Package publication incomplete'}
    @{map='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject';original=$sourceHash;saved=$srcHash;backup=$backup} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $r 'published.json') -Encoding utf8
} finally {if($locked){$mx.ReleaseMutex()};$mx.Dispose()}
