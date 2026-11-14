$ErrorActionPreference='Stop'
$r=$PSScriptRoot
$expected='918DBD37E86899009231D8DB87AC19AE165B1F68761F825D0F22CB69492C0DEA'
$p=(Resolve-Path "$r/../..").Path
$rel='Content/GameMaps/Design/L_FreightTransit_Theme_Subject.umap'
$src=Join-Path "$r/RenderHost" $rel
$dst=Join-Path $p $rel
if(!(Test-Path "$r/done-17.json") -or !(Test-Path "$r/OppositePlatform-Completed.jpg")){throw 'Saved completion or capture is missing'}
$mx=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$mx.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    if((Get-FileHash -LiteralPath $dst).Hash -ne $expected){throw 'Target was edited during completion'}
    $busy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'UnrealEditor*' -and ($_.CommandLine -match 'D:[/\\]FPS3D[/\\]FPSGAME[/\\]FPSGAME\.uproject' -or !$_.CommandLine)})
    if($busy.Count){throw 'Use the active production editor bridge'}
    $backup=Join-Path $r 'before-completion.umap'
    if(!(Test-Path -LiteralPath $backup)){[IO.File]::Copy($dst,$backup,$false)}
    if((Get-FileHash -LiteralPath $backup).Hash -ne $expected){throw 'Backup differs'}
    $tmp=$dst+'.completion.tmp'
    [IO.File]::Copy($src,$tmp,$true);$hash=(Get-FileHash -LiteralPath $src).Hash
    if((Get-FileHash -LiteralPath $tmp).Hash -ne $hash -or (Get-FileHash -LiteralPath $dst).Hash -ne $expected){throw 'Incomplete map transfer'}
    [IO.File]::Move($tmp,$dst,$true)
    if((Get-FileHash -LiteralPath $dst).Hash -ne $hash){throw 'Published map mismatch'}
    @{map='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject';original=$expected;saved=$hash;backup=$backup;receipt='done-17.json'} | ConvertTo-Json | Set-Content -LiteralPath "$r/completion-published.json" -Encoding utf8
} finally {if($held){$mx.ReleaseMutex()};$mx.Dispose()}
