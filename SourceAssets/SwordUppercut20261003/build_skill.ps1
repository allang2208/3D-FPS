$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$buildBatch = 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$records = @()
$receipt = Join-Path $PSScriptRoot 'skill_build_receipt.json'

foreach ($target in @('FPSGAME','FPSGAMEEditor')) {
    while (@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='cl.exe' OR Name='link.exe'" |
        Where-Object { $_.CommandLine -match 'FPSGAME|UnrealBuildTool' }).Count -gt 0) {
        Start-Sleep -Seconds 15
    }
    if ($target -eq 'FPSGAMEEditor') {
        $dll = Join-Path $projectRoot 'Binaries/Win64/UnrealEditor-FPSGAME.dll'
        try {
            $exclusive = [IO.File]::Open($dll, 'Open', 'ReadWrite', 'None')
            $exclusive.Dispose()
        } catch {
            $records += @{ target=$target; state='blocked_by_loaded_editor_dll'; tests_run=$false }
            $records | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $receipt -Encoding UTF8
            exit 3
        }
    }
    $log = Join-Path $PSScriptRoot ("skill-$target-$stamp.log")
    Write-Output "Building $target"
    & $buildBatch $target Win64 Development "-Project=$projectRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles "-Log=$log"
    $buildExit = $LASTEXITCODE
    $records += @{ target=$target; exit_code=$buildExit; log=$log; tests_run=$false }
    $records | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $receipt -Encoding UTF8
    if ($buildExit -ne 0) { exit $buildExit }
}
exit 0
