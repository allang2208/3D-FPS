param([int]$QueueSeconds=3600)
$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$out=$PSScriptRoot
$deadline=(Get-Date).AddSeconds($QueueSeconds)

function Get-ProjectOrBuildProcesses {
    @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe'" | Where-Object {
        ($_.Name -like 'UnrealEditor*' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME')) -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
}

function Wait-Available {
    # Wait outside the asset gate. Preserve all existing processes and unsaved work.
    while ((Get-ProjectOrBuildProcesses).Count -gt 0) {
        if ((Get-Date) -gt $deadline) { throw 'Existing project/build processes preserved; background completion pending.' }
        Start-Sleep -Seconds 5
    }
}

Write-Output 'Waiting for existing project processes and native builds to finish.'
Wait-Available
Write-Output 'Building the grounded melee approach through the ordinary editor build.'
& (Join-Path $projectRoot 'Tools/Build/Build-Editor.ps1')
$buildLog=Get-ChildItem -LiteralPath (Join-Path $projectRoot 'Saved/BuildEditor') -Filter 'build-*.log' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
@{succeeded=$true;log=$buildLog.FullName;completed_utc=[DateTime]::UtcNow.ToString('o')} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'native_build.json') -Encoding UTF8

$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    Write-Output 'Waiting for an exclusive background asset batch.'
    while (-not $held) {
        Wait-Available
        if ((Get-Date) -gt $deadline) { throw 'UE asset queue expired; installation pending.' }
        try { $held=$gate.WaitOne(1000) }
        catch [Threading.AbandonedMutexException] { $held=$true; throw 'Previous UE batch abandoned; no asset operations sent.' }
        if ($held -and (Get-ProjectOrBuildProcesses).Count -gt 0) {
            $gate.ReleaseMutex(); $held=$false
        }
    }
    Write-Output 'Importing and saving the two skins and one claw action in a background commandlet.'
    $arguments=@(($projectRoot+'\FPSGAME.uproject'),'-run=pythonscript',('-script='+$out+'\full_install.py'),
        '-unattended','-nop4','-nosplash','-nosound','-nullrhi','-multiprocess',
        '-DDC=InstalledNoZenLocalFallback','-ClawV6BackgroundImport',('-abslog='+$out+'\install.log'))
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' @arguments *> (Join-Path $out 'install_console.txt')
    $clawExit=$LASTEXITCODE
    @{exit_code=$clawExit;phase='mesh_skin_and_claw'} | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $out 'commandlet_result.json') -Encoding UTF8
    if ($clawExit -ne 0) { throw ('Asset installation failed ('+$clawExit+'); see install.log.') }
    if (-not (Test-Path -LiteralPath (Join-Path $out 'installation_complete.json'))) { throw 'Asset save completion receipt missing.' }
    Write-Output 'HUNDRED_EYED_SLAG_CLAW_V6_BUILT_AND_SAVED'
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
