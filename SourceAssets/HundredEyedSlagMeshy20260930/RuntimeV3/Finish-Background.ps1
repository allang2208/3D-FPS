param([int]$QueueSeconds=1800,[switch]$IncludeMeshes)
$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$out=Join-Path $projectRoot 'SourceAssets\HundredEyedSlagMeshy20260930\RuntimeV3'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try { $held=$gate.WaitOne([TimeSpan]::FromSeconds($QueueSeconds)) }
    catch [Threading.AbandonedMutexException] { $held=$true; throw 'Previous UE batch abandoned; no asset operations sent.' }
    if(-not $held){throw 'UE asset queue expired.'}
    $deadline=(Get-Date).AddSeconds($QueueSeconds)
    do {
        $busy=@(Get-CimInstance Win32_Process -Filter "Name LIKE 'UnrealEditor%'" | Where-Object {
            [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME'
        })
        if(-not $busy.Count){break}
        if((Get-Date) -gt $deadline){throw 'Existing FPSGAME process preserved; finish installation still pending.'}
        Start-Sleep -Seconds 10
    } while($true)
    $entry=if($IncludeMeshes){'full_install.py'}else{'finish_install.py'}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' ($projectRoot+'\FPSGAME.uproject') -run=pythonscript ('-script='+$out+'\'+$entry) -unattended -nop4 -nosplash -nosound -d3d12 -AllowCommandletRendering -RenderOffscreen ('-abslog='+$out+'\finish_install.log') *> (Join-Path $out 'finish_install_console.txt')
    if($LASTEXITCODE -ne 0){throw 'Asset completion commandlet failed; see finish_install.log.'}
    if(-not (Test-Path -LiteralPath (Join-Path $out 'installation_complete.json'))){throw 'Commandlet ended without completion receipt.'}
    Write-Output 'HUNDRED_EYED_SLAG_RUNTIME_V3_SAVED'
} finally { if($held){$gate.ReleaseMutex()}; $gate.Dispose() }
