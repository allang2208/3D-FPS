# Packaging runner (Cook + Stage + Pak/IoStore).
#
# Why this script exists: cook scope, build configuration and container policy need a
# single source of truth instead of editor UI defaults. The profile lives in
# Config/DefaultGame.ini under [/Script/UnrealEd.ProjectPackagingSettings]
# (BuildConfiguration / UsePakFile / bUseIoStore / bUseZenStore / MapsToCook).
# -Maps must match the +MapsToCook entries; the script refuses to run when they differ,
# so the command line and the pinned profile can never drift apart.
#
# Default development rule (2026-09-23): never start the editor, never run the game.
# When a project editor is already open it either refuses or queues (-WaitForEditor).
# No process is ever stopped.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Build/Build-Package.ps1 `
#     -Configuration Development -Profile core-measurement
#
#   # Queue behind an open editor, and ride out a parallel session's in-flight compile
#   # breakage instead of failing on the first error:
#   ... -WaitForEditor -RetryOnCompileFailure 8
#
#   # Compile the game target only (fast sanity check):
#   ... -SkipCook -SkipStage

param(
    [string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8',
    [ValidateSet('Development', 'Shipping', 'Test')]
    [string]$Configuration = 'Development',
    [string]$Profile = 'core-measurement',
    [string[]]$Maps = @(
        'DayNight_Lighting',
        'L_TemperateHills_Initial',
        'L_Dungeon_Prototype',
        'L_Dungeon_Generated',
        'L_Dungeon_Randomized',
        'L_Dungeon_AuthoredExpansion'
    ),
    [string]$ArchiveDir = '',
    [switch]$SkipBuild,
    [switch]$SkipCook,
    [switch]$SkipStage,
    [switch]$WithDebugInfo,
    # Multi-session host: queue behind an open editor instead of failing or
    # reaching for someone else's process.
    [switch]$WaitForEditor,
    [int]$WaitForEditorSeconds = 21600,
    # Other sessions edit sources in this working tree. A build that trips over their
    # half-finished file is a timing problem, not a verdict: retry that many extra times.
    # Cook/stage failures are never retried.
    [int]$RetryOnCompileFailure = 0,
    [int]$RetryDelaySeconds = 600,
    # Per-run cooker scheduling options; not staged as runtime game settings.
    [string]$AdditionalCookerOptions = ''
)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$projectFile = Join-Path $projectRoot 'FPSGAME.uproject'
$runUat = Join-Path $EngineRoot 'Engine/Build/BatchFiles/RunUAT.bat'
if (-not (Test-Path $runUat)) { throw "RunUAT not found: $runUat" }

# Only one writer at a time: a live editor holds the module DLLs and the assets, and
# an out-of-process cook against a live editor is a documented silent-failure path.
function Get-ProjectEditors {
    $editors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" -ErrorAction SilentlyContinue)
    @($editors | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or
        $_.CommandLine -match [regex]::Escape('FPSGAME.uproject')
    })
}

function Wait-ForFreeProject {
    $projectEditors = Get-ProjectEditors
    if ($projectEditors.Count -eq 0) { return }
    if (-not $WaitForEditor) {
        throw "FPSGAME editor is running (pid $($projectEditors.ProcessId -join ',')). Close it before packaging, or pass -WaitForEditor. No processes were stopped."
    }
    $deadline = (Get-Date).AddSeconds($WaitForEditorSeconds)
    Write-Output "waiting for project editor to exit: pid $($projectEditors.ProcessId -join ',') (limit $WaitForEditorSeconds s)"
    while ($projectEditors.Count -gt 0) {
        if ((Get-Date) -gt $deadline) {
            throw "project editor still running after $WaitForEditorSeconds s (pid $($projectEditors.ProcessId -join ',')). No processes were stopped."
        }
        Start-Sleep -Seconds 20
        $projectEditors = Get-ProjectEditors
    }
    # Handles and the DDC can still be settling right after exit; also make sure
    # nobody immediately reopened the project before we start writing.
    Start-Sleep -Seconds 15
    $projectEditors = Get-ProjectEditors
    while ($projectEditors.Count -gt 0) {
        Write-Output "editor came back: pid $($projectEditors.ProcessId -join ',')"
        if ((Get-Date) -gt $deadline) {
            throw "project editor kept running past the wait limit. No processes were stopped."
        }
        Start-Sleep -Seconds 20
        $projectEditors = Get-ProjectEditors
    }
    Write-Output 'editor is gone; proceeding with packaging'
}

Wait-ForFreeProject

if ([string]::IsNullOrWhiteSpace($ArchiveDir)) {
    $ArchiveDir = Join-Path $projectRoot ("Saved/StagedBuilds/" + $Profile + "-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
}
$logDir = Join-Path $projectRoot 'Saved/BuildPackage'
New-Item -ItemType Directory -Force -Path $logDir, $ArchiveDir | Out-Null
$logFile = Join-Path $logDir ($Profile + '-' + $Configuration + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')

# The ini map list must be exactly the map list requested here; otherwise cook scope
# silently drifts away from the pinned profile.
$gameIni = Join-Path $projectRoot 'Config/DefaultGame.ini'

# Keep the real package path for every entry, not just a short name. The cook
# argument must be built from what the ini actually points at: maps outside
# /Game/GameMaps/ (for example /Game/Tests/HangingBellM09/L_M09CeilingTest) used to
# be rewritten into /Game/GameMaps/<rest> and were then skipped by the cook with
# only "Unable to find package for cooking" in the log, so the build shipped
# without them while still reporting the profile as pinned.
$iniMapPaths = [ordered]@{}
Select-String -Path $gameIni -Pattern '^\+MapsToCook=\(FilePath="(/Game/[^"]+)"\)' -AllMatches |
    ForEach-Object { $_.Matches } |
    ForEach-Object {
        $fullPath = $_.Groups[1].Value
        $shortName = $fullPath -replace '^/Game/(?:GameMaps/)?', ''
        if ($iniMapPaths.Contains($shortName)) {
            if ($iniMapPaths[$shortName] -ne $fullPath) {
                throw ("Config/DefaultGame.ini maps two different packages to the same " +
                       "'-Maps $shortName' shorthand: $($iniMapPaths[$shortName]) and $fullPath. " +
                       'Pass distinct paths or remove one entry.')
            }
        } else {
            $iniMapPaths[$shortName] = $fullPath
        }
    }
$iniMaps = @($iniMapPaths.Keys)
if ($iniMaps.Count -eq 0) {
    throw 'Config/DefaultGame.ini has no +MapsToCook entries; refusing to cook with implicit scope.'
}
$onlyInCommand = @($Maps | Where-Object { $iniMaps -notcontains $_ })
$onlyInIni = @($iniMaps | Where-Object { $Maps -notcontains $_ })
if ($onlyInCommand.Count -gt 0 -or $onlyInIni.Count -gt 0) {
    throw ("Map scope mismatch between -Maps and Config/DefaultGame.ini. " +
           "only in command: [$($onlyInCommand -join ', ')]; only in ini: [$($onlyInIni -join ', ')]")
}

$mapArg = ($Maps | ForEach-Object { $iniMapPaths[$_] }) -join '+'

# Fail before cooking if an ini entry points at a package that does not exist.
# A missing map is otherwise only a warning in the cook log, which is how the
# stale path above stayed unnoticed.
foreach ($rel in $Maps) {
    $pkg = $iniMapPaths[$rel] -replace '^/Game/', ''
    $umap = Join-Path $projectRoot ("Content/$pkg.umap")
    if (-not (Test-Path -LiteralPath $umap)) {
        throw "Config/DefaultGame.ini lists $($iniMapPaths[$rel]) but $umap does not exist; refusing to cook a map that cannot be loaded."
    }
}

# Runtime paths held in strings/JSON are not a map dependency. These known
# required packages must have source inputs and appear in the completed cook.
$requiredRuntimePackages = @()
if (-not $SkipCook) {
    $runtimeManifest = Join-Path $projectRoot 'Config/Packaging/RequiredRuntimePackages.txt'
    $requiredRuntimePackages = @(Get-Content -LiteralPath $runtimeManifest |
        ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') } |
        Sort-Object -Unique)
    foreach ($package in $requiredRuntimePackages) {
        if ($package -notmatch '^/Game/[A-Za-z0-9_/]+$') {
            throw "Invalid required runtime package in ${runtimeManifest}: $package"
        }
        $sourceBase = Join-Path $projectRoot ('Content/' + $package.Substring(6))
        if (-not (Test-Path -LiteralPath ($sourceBase + '.uasset')) -and
            -not (Test-Path -LiteralPath ($sourceBase + '.umap'))) {
            throw "Required runtime package has no source file: $package"
        }
    }
}

$uatArgs = @(
    'BuildCookRun',
    "-project=$projectFile",
    '-noP4',
    '-utf8output',
    '-platform=Win64',
    '-targetplatform=Win64',
    "-clientconfig=$Configuration",
    '-nocompileeditor',
    '-noprereqs',
    '-archive',
    "-archivedirectory=$ArchiveDir"
)
if (-not $WithDebugInfo) { $uatArgs += '-nodebuginfo' }
if (-not $SkipBuild) { $uatArgs += '-build' }
if (-not $SkipCook) { $uatArgs += @('-cook', "-map=$mapArg") }
if (-not $SkipCook -and -not [string]::IsNullOrWhiteSpace($AdditionalCookerOptions)) {
    $uatArgs += "-AdditionalCookerOptions=$AdditionalCookerOptions"
}
if (-not $SkipStage) { $uatArgs += @('-stage', '-pak', '-iostore') }
if ($SkipCook -and -not $SkipStage) { throw '-SkipStage is required when -SkipCook is set (staging needs cooked data).' }

Write-Output "profile      : $Profile"
Write-Output "configuration: $Configuration"
Write-Output "maps ($($Maps.Count))    : $($Maps -join ', ')"
Write-Output "archive      : $ArchiveDir"
Write-Output "log          : $logFile"

# RunUAT is a batch file. Start-Process does not reliably surface its exit code on
# this host (it reported an empty code for a failed build), so invoke it through the
# call operator and read $LASTEXITCODE.
$attempt = 0
$code = 1
while ($true) {
    $attempt++
    Wait-ForFreeProject
    $started = Get-Date
    & $runUat @uatArgs *> $logFile
    $code = $LASTEXITCODE
    $elapsed = (Get-Date) - $started
    Write-Output ("attempt {0}: exit {1}  elapsed {2:hh\:mm\:ss}" -f $attempt, $code, $elapsed)
    if ($code -eq 0) { break }

    Write-Output '--- last 25 log lines ---'
    Get-Content $logFile -Tail 25 -ErrorAction SilentlyContinue

    $compileFailure = @(Select-String -Path $logFile -Pattern 'OtherCompilationError|error C[0-9]{4}|error LNK[0-9]{4}|error MSB[0-9]{4}' -ErrorAction SilentlyContinue).Count -gt 0
    if (-not $compileFailure) {
        Write-Output 'failure is not a compile error; not retrying'
        break
    }
    if ($attempt -gt $RetryOnCompileFailure) {
        Write-Output "compile error and no retries left (RetryOnCompileFailure=$RetryOnCompileFailure)"
        break
    }
    Write-Output "compile error, likely a parallel session's in-flight edit; retrying in $RetryDelaySeconds s (attempt $attempt of $($RetryOnCompileFailure + 1))"
    Start-Sleep -Seconds $RetryDelaySeconds
}

Write-Output "log: $logFile"
if ($code -ne 0) { exit $code }
if (-not $SkipCook) {
    # Cook can succeed while shipping a default material for shader failures.
    # Preserve the authored appearance: treat that build diagnostic as failure.
    $materialFailures = @(Select-String -LiteralPath $logFile -Pattern 'Failed to compile Material.*Default Material will be used in game' |
        ForEach-Object { $_.Line } | Sort-Object -Unique)
    if ($materialFailures.Count) {
        $materialFailurePath = [IO.Path]::ChangeExtension($logFile, 'material-failures.txt')
        $materialFailures | Set-Content -LiteralPath $materialFailurePath -Encoding utf8
        throw "Cook produced fallback materials. Repair the shader errors before delivery: $materialFailurePath"
    }
    # ReferencedSet belongs to this full Windows cook. Read package identities
    # rather than accepting an old loose cooked file as proof of inclusion.
    $referencedSetPath = Join-Path $projectRoot 'Saved/Cooked/Windows/FPSGAME/Metadata/ReferencedSet.txt'
    $cookedPackages = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($package in Get-Content -LiteralPath $referencedSetPath) {
        [void]$cookedPackages.Add($package.Trim())
    }
    $missingRuntimePackages = @($requiredRuntimePackages | Where-Object { -not $cookedPackages.Contains($_) })
    $coveragePath = [IO.Path]::ChangeExtension($logFile, 'runtime-packages.json')
    [ordered]@{required_count=$requiredRuntimePackages.Count;missing=$missingRuntimePackages;
        referenced_set=$referencedSetPath;archive=$ArchiveDir;runtime_tested=$false} |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $coveragePath -Encoding utf8
    if ($missingRuntimePackages.Count) {
        throw "Cook omitted required runtime packages: $($missingRuntimePackages -join ', '). Details: $coveragePath"
    }
    Write-Output "required runtime packages cooked: $($requiredRuntimePackages.Count)"
}
Write-Output "staged build: $(Join-Path $ArchiveDir 'Windows')"
