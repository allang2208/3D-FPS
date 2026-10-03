$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$buildBatch = 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
$outputDirectory = Join-Path $projectRoot 'Saved\BuildSurvival20261003'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
$deadline = (Get-Date).AddMinutes(60)
$announced = $false
while ($true) {
    $processes = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='FPSGAME.exe'")
    $busy = @($processes | Where-Object {
        $_.Name -eq 'UnrealEditor.exe' -or $_.Name -eq 'UnrealEditor-Cmd.exe' -or $_.Name -eq 'FPSGAME.exe' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if ($busy.Count -eq 0) { break }
    if (-not $announced) { Write-Output 'Waiting for existing UE processes/builds to release the build window. No process will be stopped.'; $announced = $true }
    if ((Get-Date) -ge $deadline) { throw 'Build window remains occupied. Sources and UI references are saved; native build has not started.' }
    Start-Sleep -Seconds 20
}
foreach ($target in @('FPSGAMEEditor','FPSGAME')) {
    $logFile = Join-Path $outputDirectory ($target + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
    Write-Output "Building $target; log: $logFile"
    # Ordinary dependency tracking is required after adding reflected profile/UMG members.
    & $buildBatch $target Win64 Development "-Project=$projectRoot\FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE "-Log=$logFile"
    if ($LASTEXITCODE -ne 0) { throw "$target build failed with exit code $LASTEXITCODE. See $logFile" }
}
Write-Output 'Editor and Game binaries saved. No editor, game, or tests were launched.'
