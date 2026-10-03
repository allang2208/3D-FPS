param([int]$QueueSeconds=1800,[switch]$AnimationsOnly)
$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$out=$PSScriptRoot
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    Write-Output 'Waiting for the UE asset batch gate.'
    try { $held=$gate.WaitOne([TimeSpan]::FromSeconds($QueueSeconds)) }
    catch [Threading.AbandonedMutexException] { $held=$true; throw 'Previous UE batch abandoned; no asset operations sent.' }
    if(-not $held){throw 'UE asset queue expired.'}
    $deadline=(Get-Date).AddSeconds($QueueSeconds)
    do {
        $busy=@(Get-CimInstance Win32_Process -Filter "Name LIKE 'UnrealEditor%'" | Where-Object {
            [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME'
        })
        if(-not $busy.Count){break}
        if((Get-Date) -gt $deadline){throw 'Existing FPSGAME process preserved; installation pending.'}
        Start-Sleep -Seconds 10
    } while($true)
    Write-Output 'Importing HeroHandV4 using a background commandlet.'
    # Asset-only import does not require platform SDK validation through Build.bat's compile lock.
    $arguments=@(($projectRoot+'\FPSGAME.uproject'),'-run=pythonscript',('-script='+$out+'\full_install.py'),
        '-unattended','-nop4','-nosplash','-nosound','-nullrhi','-multiprocess','-DDC=InstalledNoZenLocalFallback',
        '-HeroHandBackgroundImport',('-abslog='+$out+'\install.log'))
    if($AnimationsOnly){$arguments+='-HeroHandAnimationsOnly'}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' @arguments *> (Join-Path $out 'install_console.txt')
    $nativeExit=$LASTEXITCODE
    @{exit_code=$nativeExit;phase=if($AnimationsOnly){'animations'}else{'full'}} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'commandlet_result.json') -Encoding UTF8
    if($nativeExit -ne 0){throw ('Asset installation commandlet failed ('+$nativeExit+'); see install.log.')}
    Write-Output 'HUNDRED_EYED_SLAG_HERO_HAND_V4_SAVED'
} finally { if($held){$gate.ReleaseMutex()}; $gate.Dispose() }
