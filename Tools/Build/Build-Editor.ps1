param(
    [string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8'
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
& $buildBatch FPSGAMEEditor Win64 Development "-Project=$projectFile" -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles "-Log=$buildLog"
if ($LASTEXITCODE -ne 0) {
    throw "Editor build failed with exit code $LASTEXITCODE. See $buildLog"
}
Write-Output "Editor modules built. Runtime testing remains manual. Log: $buildLog"
