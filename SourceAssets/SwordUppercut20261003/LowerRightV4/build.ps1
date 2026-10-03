$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$records = @()
$receipt = Join-Path $PSScriptRoot 'build_receipt.json'
foreach ($target in @('FPSGAME','FPSGAMEEditor')) {
    $activeBuilds = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='cl.exe' OR Name='link.exe'" |
        Where-Object { $_.CommandLine -match 'FPSGAME|UnrealBuildTool' })
    if ($activeBuilds.Count -gt 0) { Write-Output 'Another build is active; no overlapping build started.'; exit 2 }
    if ($target -eq 'FPSGAMEEditor') {
        $dll = Join-Path $projectRoot 'Binaries/Win64/UnrealEditor-FPSGAME.dll'
        try {
            $exclusive = [IO.File]::Open($dll,'Open','ReadWrite','None')
            $exclusive.Dispose()
        } catch {
            $records += @{target=$target;state='blocked_by_loaded_editor_dll';tests_run=$false}
            $records | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $receipt -Encoding UTF8
            exit 3
        }
    }
    $log = Join-Path $PSScriptRoot ($target+'-build.log')
    Write-Output ('Building '+$target)
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $target Win64 Development "-Project=$projectRoot/FPSGAME.uproject" -NoLiveCoding -NoHotReload -NoHotReloadFromIDE "-Log=$log"
    $result = $LASTEXITCODE
    $records += @{target=$target;exit_code=$result;log=$log;tests_run=$false}
    $records | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $receipt -Encoding UTF8
    if ($result -ne 0) {exit $result}
}
exit 0
