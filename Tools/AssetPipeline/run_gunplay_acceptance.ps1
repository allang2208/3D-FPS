param(
    [ValidateSet(30, 60, 144)][int]$Fps = 60,
    [string]$Label = '',
    [int]$Width = 1280,
    [int]$Height = 720,
    [switch]$CaptureFrames,
    [switch]$RealTime,
    [ValidateRange(0, 300)][int]$HitchMs = 0
)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$editorExe = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
if (!$Label) { $Label = $(if ($RealTime) { 'realtime' } else { 'fps' + $Fps }) + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss') }
if ($Label -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Label must contain only letters, digits, underscores or hyphens.' }
$outputDir = Join-Path $projectRoot ('Saved/GunplayUpgrade/' + $Label)
if (Test-Path -LiteralPath $outputDir) { throw "Output already exists; choose a new label: $outputDir" }
$logPath = Join-Path $projectRoot ('SourceAssets/GunplayUpgrade/runtime-' + $Label + '.log')
$arguments = @(
    ('"' + (Join-Path $projectRoot 'FPSGAME.uproject') + '"'),
    '/Game/GameMaps/DayNight_Lighting', '-game', '-windowed',
    ('-ResX=' + $Width), ('-ResY=' + $Height), '-unattended', '-nosplash',
    '-GunplayAudit', ('-GunplayLabel=' + $Label),
    '-FixedSeed', ('-abslog="' + $logPath + '"')
)
if (!$RealTime) { $arguments += @('-UseFixedTimeStep', ('-FPS=' + $Fps)) }
if ($CaptureFrames) { $arguments += '-GunplayCaptureFrames' }
if ($HitchMs -gt 0) { $arguments += ('-GunplayHitchMs=' + $HitchMs) }
$testProcess = Start-Process -FilePath $editorExe -ArgumentList $arguments -WindowStyle Hidden -PassThru
$clockDescription = if ($RealTime) { 'elapsed game time, variable delta' } else { "fixed $Fps Hz" }
Write-Output "Gunplay audit process $($testProcess.Id), $clockDescription, label $Label"
# Only wait for this newly created standalone game; never stop another editor.
$testProcess.WaitForExit()
$assertionsPath = Join-Path $outputDir 'assertions.log'
if (!(Test-Path -LiteralPath $assertionsPath)) { throw "No assertion output. Inspect $logPath" }
$results = Get-Content -LiteralPath $assertionsPath
$passCount = @($results | Where-Object { $_ -match '^GUNPLAY_ASSERT PASS ' }).Count
$failCount = @($results | Where-Object { $_ -match '^GUNPLAY_ASSERT FAIL ' }).Count
$complete = @($results | Where-Object { $_ -match '^GUNPLAY_ACCEPTANCE_COMPLETE failures=0 ' }).Count -eq 1
$summary = [ordered]@{
    label = $Label; simulation_hz = $(if ($RealTime) { $null } else { $Fps }); real_time = [bool]$RealTime; width = $Width; height = $Height
    process_exit = $testProcess.ExitCode; pass = $passCount; fail = $failCount
    completion_marker = $complete; assertions = $assertionsPath; runtime_log = $logPath; injected_hitch_ms = $HitchMs
    note = "$clockDescription; simulated PlayerController inputs, not an FPS benchmark or human playthrough."
}
$summary | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputDir 'result.json') -Encoding utf8
$summary | ConvertTo-Json | Write-Output
if ($testProcess.ExitCode -ne 0 -or !$complete -or $failCount -gt 0 -or $passCount -eq 0) { exit 1 }
