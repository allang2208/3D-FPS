$ErrorActionPreference='Stop'
$r=$PSScriptRoot
$expected='0C6AF927086F2FD9C9EA4A33D91C4A6839A5B5020FFBECB63AE8EAD85F5E2EC8'
$p=(Resolve-Path "$r/../..").Path
$rel='Content/GameMaps/Design/L_FreightTransit_Theme_Subject.umap'
$src=Join-Path "$r/RenderHost" $rel
$dst=Join-Path $p $rel
if(!(Test-Path "$r/done-15.json") -or !(Test-Path "$r/delivery-capture.json") -or !(Test-Path "$r/Compare_PlatformWallAndFloor.jpg")){throw 'Saved assets or comparison missing'}
$mx=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$mx.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    if((Get-FileHash -LiteralPath $dst).Hash -ne $expected){throw 'Production map changed during authoring'}
    $busy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'UnrealEditor*' -and ($_.CommandLine -match 'D:[/\\]FPS3D[/\\]FPSGAME[/\\]FPSGAME\.uproject' -or !$_.CommandLine)})
    if($busy.Count){throw 'Production editor is active; use its bridge'}
    $backup=Join-Path $r 'prior-map.umap'
    if(!(Test-Path -LiteralPath $backup)){[IO.File]::Copy($dst,$backup,$false)}
    if((Get-FileHash -LiteralPath $backup).Hash -ne $expected){throw 'Backup differs'}
    $tmp=$dst+'.stationfinish.tmp'
    [IO.File]::Copy($src,$tmp,$true)
    $hash=(Get-FileHash -LiteralPath $src).Hash
    if((Get-FileHash -LiteralPath $tmp).Hash -ne $hash -or (Get-FileHash -LiteralPath $dst).Hash -ne $expected){throw 'Map transfer incomplete'}
    [IO.File]::Move($tmp,$dst,$true)
    if((Get-FileHash -LiteralPath $dst).Hash -ne $hash){throw 'Map transfer mismatch'}
    @{map='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject';original=$expected;saved=$hash;backup=$backup;assets='done-15.json';skirting='original mesh with localized patina';captures='delivery-capture.json';gameplay_test=$false} | ConvertTo-Json | Set-Content -LiteralPath "$r/published.json" -Encoding utf8
} finally {if($held){$mx.ReleaseMutex()};$mx.Dispose()}
