param(
    [string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8',
    [switch]$RecompileGameplay
)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$projectFile = Join-Path $projectRoot 'FPSGAME.uproject'
$buildBatch = Join-Path $EngineRoot 'Engine/Build/BatchFiles/Build.bat'

# Build the complete dependency graph with ordinary DLL names. A game-only
# ModuleWithSuffix build can leave a plugin import pointing at an older DLL.
$editors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'")
$projectEditors = @($editors | Where-Object {
    [string]::IsNullOrWhiteSpace($_.CommandLine) -or
    $_.CommandLine -match [regex]::Escape('FPSGAME.uproject')
})
if ($projectEditors.Count -gt 0) {
    throw 'Save your work and close the FPSGAME editor before building. No processes were stopped.'
}

$logDirectory = Join-Path $projectRoot 'Saved/BuildEditor'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$buildLog = Join-Path $logDirectory ('build-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$buildArguments = @('FPSGAMEEditor', 'Win64', 'Development', "-Project=$projectFile", '-WaitMutex', '-NoHotReload', '-NoHotReloadFromIDE', '-NoUBTMakefiles', "-Log=$buildLog")
if ($RecompileGameplay) {
    # Recover from mixed AFPSGAMECharacter layouts across translation units.
    # Invalidate generated object files only; retain source, Content and saves.
    $activeBuilds = @(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
        $_.Name -eq 'UnrealBuildTool.exe' -or $_.Name -eq 'cl.exe' -or $_.Name -eq 'link.exe'
    })
    if ($activeBuilds.Count -gt 0) { throw 'A native build is active. No object files were removed; retry after it finishes.' }
    $recoveryDirectory = Join-Path $logDirectory ('layout-recovery-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Path $recoveryDirectory -Force | Out-Null
    foreach ($file in @('UnrealEditor-FPSGAME.dll', 'UnrealEditor-FPSGAME.pdb')) {
        $binary = Join-Path $projectRoot ('Binaries/Win64/' + $file)
        if (Test-Path -LiteralPath $binary) { Copy-Item -LiteralPath $binary -Destination $recoveryDirectory }
    }
    $projectPrefix = $projectRoot.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    $objects = @()
    foreach ($relative in @(
        'Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME',
        'Plugins/ColdSteelNet/Intermediate/Build/Win64/x64/UnrealEditor/Development/ColdSteelNet'
    )) {
        $directory = [IO.Path]::GetFullPath((Join-Path $projectRoot $relative))
        if (-not $directory.StartsWith($projectPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw "Recovery path is outside the project: $directory" }
        if (Test-Path -LiteralPath $directory) {
            $objects += @(Get-ChildItem -LiteralPath $directory -File -Filter '*.obj')
        }
    }
    $objects | Select-Object FullName, Length, LastWriteTimeUtc | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $recoveryDirectory 'invalidated-objects.json') -Encoding utf8
    foreach ($object in $objects) { Remove-Item -LiteralPath $object.FullName -Force }
    # Recompile directly from the current headers instead of restoring cached
    # UBA output. UHT and both modules then link into the ordinary Editor DLLs.
    $buildArguments += @('-NoUBA', '-ForceHeaderGeneration')
    Write-Output "Recompiling gameplay modules from source ($($objects.Count) generated objects invalidated). Previous DLL/PDB: $recoveryDirectory"
}
& $buildBatch @buildArguments
if ($LASTEXITCODE -ne 0) {
    throw "Editor build failed with exit code $LASTEXITCODE. See $buildLog"
}
Write-Output "Editor modules built. Runtime testing remains manual. Log: $buildLog"
