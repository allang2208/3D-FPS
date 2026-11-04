$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$buildBatch = 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
$completed = @()
foreach ($target in @('FPSGAMEEditor', 'FPSGAME')) {
    $busy = @(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -in @('UnrealEditor.exe', 'UnrealEditor-Cmd.exe', 'FPSGAME.exe', 'UnrealBuildTool.exe', 'cl.exe', 'link.exe')) -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if ($busy.Count) { throw 'Editor, game or native build is active. No processes were stopped.' }
    $buildLog = Join-Path $PSScriptRoot ($target + '.log')
    $buildArguments = @($target, 'Win64', 'Development', "-Project=$projectRoot/FPSGAME.uproject", '-WaitMutex', "-Log=$buildLog")
    if ($target -eq 'FPSGAMEEditor') { $buildArguments += @('-NoHotReload', '-NoHotReloadFromIDE', '-NoUBTMakefiles') }
    & $buildBatch @buildArguments
    $buildExit = $LASTEXITCODE
    $completed += @{ target=$target; exit_code=$buildExit; log=$buildLog; completed_at=(Get-Date -Format o) }
    @{ builds=$completed; gameplay_tested=$false } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Encoding utf8
    if ($buildExit -ne 0) { throw "$target build failed with exit code $buildExit" }
}
