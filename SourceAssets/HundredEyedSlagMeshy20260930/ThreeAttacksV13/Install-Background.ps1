param([int]$QueueSeconds=3600)
$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$out=$PSScriptRoot
$projectNormalized=($projectRoot+'\FPSGAME.uproject').Replace('\','/').ToLowerInvariant()
$deadline=(Get-Date).AddSeconds($QueueSeconds)
$newAssetsOnly=-not (Test-Path -LiteralPath (Join-Path $projectRoot 'Content\Monsters\HundredEyedSlag\ThreeAttacksV13'))

function Get-PrimaryProcesses {
    @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or
        $_.CommandLine.Replace('\','/').ToLowerInvariant().Contains($projectNormalized) -or
        $_.CommandLine.Replace('\','/').ToLowerInvariant().Contains('d:/fps3d/fpsgame-mp/') -or
        $_.CommandLine -match '(?i)(?:^|[\s"\/])FPSGAME\.uproject(?:[\s"]|$)'
    })
}
function Get-NativeBuilds {
    @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object { $_.CommandLine -match 'UnrealBuildTool' })
}
function Get-BlockingEditors {
    @(Get-PrimaryProcesses | Where-Object {
        -not $newAssetsOnly -or [string]::IsNullOrWhiteSpace($_.CommandLine) -or
        -not $_.CommandLine.Replace('\','/').ToLowerInvariant().Contains('d:/fps3d/fpsgame-mp/')
    })
}

Write-Output 'Waiting outside the asset mutex for the ongoing native build.'
while ((Get-NativeBuilds).Count -gt 0) {
    if ((Get-Date) -gt $deadline) { throw 'Native build still running; prepared recovery assets preserved.' }
    Start-Sleep -Seconds 5
}
$primary=@(Get-PrimaryProcesses)
$interactive=@($primary | Where-Object { $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)\s-game(?:\s|$)' -and $_.CommandLine.Replace('\','/').ToLowerInvariant().Contains($projectNormalized) })
if ($interactive.Count -eq 1) {
    Write-Output 'Saving idle laser clips and red material through the existing editor asset batch.'
    & (Join-Path $out 'Save-InExistingEditor.ps1') -QueueSeconds $QueueSeconds
    if ($LASTEXITCODE -ne 0) { throw 'Editor bridge installation did not complete; current editor preserved.' }
    return
}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    Write-Output 'Waiting for shared asset access; active project instances are preserved.'
    while (-not $held) {
        if ((Get-Date) -gt $deadline) { throw 'Asset queue expired; prepared recovery assets preserved.' }
        if ((Get-BlockingEditors).Count -gt 0 -or (Get-NativeBuilds).Count -gt 0) { Start-Sleep -Seconds 5; continue }
        try { $held=$gate.WaitOne(1000) }
        catch [Threading.AbandonedMutexException] { $held=$true; throw 'Previous batch abandoned; no asset operation sent.' }
        if ($held -and ((Get-BlockingEditors).Count -gt 0 -or (Get-NativeBuilds).Count -gt 0)) {
            $gate.ReleaseMutex(); $held=$false
        }
    }
    Write-Output 'Saving three idle laser clips and the red charge material; shared mesh and skeleton stay read-only.'
    $arguments=@(($projectRoot+'\FPSGAME.uproject'),'-run=pythonscript',('-script='+$out+'\install_assets.py'),
        '-unattended','-nop4','-nosplash','-nosound','-nullrhi','-multiprocess',
        '-DDC=InstalledNoZenLocalFallback',('-abslog='+$out+'\install.log'))
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' @arguments *> (Join-Path $out 'install_console.txt')
    $rampageExit=$LASTEXITCODE
    @{exit_code=$rampageExit;phase='three_idle_laser_clips_and_red_material'} | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $out 'commandlet_result.json') -Encoding utf8BOM
    if ($rampageExit -ne 0) { throw ('Background installation failed ('+$rampageExit+'); see install.log.') }
    if (-not (Test-Path -LiteralPath (Join-Path $out 'ready_assets.json'))) { throw 'Asset save completion receipt missing.' }
    Write-Output 'SLAG_V13_INSTALLED_AND_SAVED'
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
