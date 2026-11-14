param([Parameter(Mandatory=$true)][string]$Receipt)
$ErrorActionPreference='Stop'
$r=$PSScriptRoot
$p=(Resolve-Path "$r/../..").Path
$expected='45680D7855CEC7F60C9C1D9036B743434BAC54B251617B6C263EB55625A84A76'
$rel='Content/GameMaps/Design/L_FreightTransit_Theme_Subject.umap'
if(!(Test-Path -LiteralPath (Join-Path $r $Receipt)) -or !(Test-Path -LiteralPath (Join-Path $r 'OppositePlatform-Before-After.jpg'))){throw 'Saved work or comparison not ready'}
$src=Join-Path "$r/RenderHost" $rel
$dst=Join-Path $p $rel
$mx=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$mx.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    if((Get-FileHash $dst).Hash -ne $expected){throw 'Live map was edited during the pass'}
    $busy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'UnrealEditor*' -and ($_.CommandLine -match 'D:[/\\]FPS3D[/\\]FPSGAME[/\\]FPSGAME\.uproject' -or !$_.CommandLine)})
    if($busy.Count){throw 'Use the existing production editor bridge'}
    $backup=Join-Path $r 'prior-map.umap';$tmp=$dst+'.oppositeplatform.tmp'
    if(!(Test-Path $backup)){[IO.File]::Copy($dst,$backup,$false)}
    if((Get-FileHash $backup).Hash -ne $expected){throw 'Conflicting original backup'}
    [IO.File]::Copy($src,$tmp,$true);$hash=(Get-FileHash $src).Hash
    if((Get-FileHash $tmp).Hash -ne $hash -or (Get-FileHash $dst).Hash -ne $expected){throw 'Package changed during transfer'}
    [IO.File]::Move($tmp,$dst,$true)
    if((Get-FileHash $dst).Hash -ne $hash){throw 'Saved map mismatch'}
    @{map='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject';original=$expected;saved=$hash;backup=$backup;receipt=$Receipt} | ConvertTo-Json | Set-Content -LiteralPath "$r/published.json" -Encoding utf8
} finally {if($held){$mx.ReleaseMutex()};$mx.Dispose()}
