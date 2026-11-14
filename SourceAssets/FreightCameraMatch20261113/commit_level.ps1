$ErrorActionPreference='Stop'
$project='D:\FPS3D\FPSGAME'
$rel='Content\GameMaps\Design\L_FreightTransit_Theme_Subject.umap'
$src=Join-Path (Join-Path $PSScriptRoot 'RenderHost') $rel
$dest=Join-Path $project $rel
$backup=Join-Path $PSScriptRoot 'before-original.umap'
$expected='B6CC5D43DD6796D1C9B842FFB2FC198B4FF049222775C900B35737CC4F33979B'
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$acquired=$false
try {
    try {$acquired=$mutex.WaitOne()} catch [Threading.AbandonedMutexException] {$acquired=$true}
    $release=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'private-save.json') | ConvertFrom-Json
    if((Get-FileHash -LiteralPath $src).Hash -ne $release.hash -or (Get-FileHash -LiteralPath $dest).Hash -ne $expected){throw 'Source map or original changed'}
    $editors=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'UnrealEditor*' -and ($_.CommandLine -match 'D:[/\\]FPS3D[/\\]FPSGAME[/\\]FPSGAME\.uproject' -or -not $_.CommandLine)})
    if ($editors.Count){throw 'Use live bridge publication for loaded project'}
    if (-not (Test-Path -LiteralPath $backup)){[IO.File]::Copy($dest,$backup)}
    if ((Get-FileHash -LiteralPath $backup).Hash -ne $expected){throw 'Original backup mismatch'}
    $temp=$dest+'.freight-match.tmp'
    [IO.File]::Copy($src,$temp,$true)
    if((Get-FileHash -LiteralPath $temp).Hash -ne $release.hash -or (Get-FileHash -LiteralPath $dest).Hash -ne $expected){throw 'Map changed during staging'}
    [IO.File]::Replace($temp,$dest,$dest+'.freight-match-rollback',$true)
    $rollback=$dest+'.freight-match-rollback'
    if ((Get-FileHash -LiteralPath $rollback).Hash -eq $expected){Remove-Item -LiteralPath $rollback}
    @{map='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject';saved=(Get-FileHash -LiteralPath $dest).Hash;original=$expected;backup=$backup;method='identical_photographed_package'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'published.json') -Encoding UTF8
} finally {if($acquired){$mutex.ReleaseMutex()};$mutex.Dispose()}
