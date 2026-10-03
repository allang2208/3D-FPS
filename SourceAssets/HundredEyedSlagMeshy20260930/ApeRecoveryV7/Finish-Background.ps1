param([int]$QueueSeconds=1800)
$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$out=$PSScriptRoot
$projectNormalized=($projectRoot+'\FPSGAME.uproject').Replace('\','/').ToLowerInvariant()
$deadline=(Get-Date).AddSeconds($QueueSeconds)

function Get-PrimaryProcesses {
    @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or
        $_.CommandLine.Replace('\','/').ToLowerInvariant().Contains($projectNormalized) -or
        # FPSGAME-mp currently holds a shared Content junction; its game processes
        # can lock these same assets even though the project filenames differ.
        $_.CommandLine.Replace('\','/').ToLowerInvariant().Contains('d:/fps3d/fpsgame-mp/fpsgame.uproject')
    })
}
function Get-NativeBuilds {
    @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object { $_.CommandLine -match 'UnrealBuildTool' })
}

# Use a live primary editor through the existing bridge, or a background commandlet.
# Account for game instances in the Content-sharing FPSGAME-mp checkout as well.
while ((Get-NativeBuilds).Count -gt 0) {
    if ((Get-Date) -gt $deadline) { throw 'Native build still running; asset installation pending.' }
    Start-Sleep -Seconds 5
}
$primary=@(Get-PrimaryProcesses)
$interactive=@($primary | Where-Object { $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)\s-game(?:\s|$)' })
if ($interactive.Count -eq 1) {
    Write-Output 'Saving the repair through the running primary editor asset batch.'
    & (Join-Path $projectRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript (Join-Path $out 'full_install.py') `
        -QueueWaitSeconds $QueueSeconds -OutputFile (Join-Path $out ('install_bridge-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.txt')) -MaxOutputChars 2200
    if ($LASTEXITCODE -ne 0) { throw 'Editor bridge installation did not complete; existing editor preserved.' }
    return
}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    Write-Output 'Waiting for the shared UE asset batch, outside all existing game processes.'
    while (-not $held) {
        if ((Get-Date) -gt $deadline) { throw 'Asset queue expired; installation pending.' }
        if ((Get-PrimaryProcesses).Count -gt 0 -or (Get-NativeBuilds).Count -gt 0) { Start-Sleep -Seconds 5; continue }
        try { $held=$gate.WaitOne(1000) }
        catch [Threading.AbandonedMutexException] { $held=$true; throw 'Previous batch abandoned; no asset operation sent.' }
        if ($held -and ((Get-PrimaryProcesses).Count -gt 0 -or (Get-NativeBuilds).Count -gt 0)) {
            $gate.ReleaseMutex(); $held=$false
        }
    }
    Write-Output 'Importing two repaired skins and two attacks in the primary project commandlet.'
    $arguments=@(($projectRoot+'\FPSGAME.uproject'),'-run=pythonscript',('-script='+$out+'\full_install.py'),
        '-unattended','-nop4','-nosplash','-nosound','-nullrhi','-multiprocess',
        '-DDC=InstalledNoZenLocalFallback',('-abslog='+$out+'\install.log'))
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' @arguments *> (Join-Path $out 'install_console.txt')
    $apeExit=$LASTEXITCODE
    @{exit_code=$apeExit;phase='arclength_skin_and_two_attacks'} | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $out 'commandlet_result.json') -Encoding UTF8
    if ($apeExit -ne 0) { throw ('Background installation failed ('+$apeExit+'); see install.log.') }
    if (-not (Test-Path -LiteralPath (Join-Path $out 'installation_complete.json'))) { throw 'Asset save completion receipt missing.' }
    Write-Output 'APE_RECOVERY_V7_INSTALLED_AND_SAVED'
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
