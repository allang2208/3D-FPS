$ErrorActionPreference = 'Stop'
$taskRoot = 'D:\FPS3D\FPSGAME'
$receiptDir = Join-Path $taskRoot 'SourceAssets\LightningHaste20261019'
Set-Location -LiteralPath $taskRoot
function Wait-FreeBuild {
    while ($true) {
        $busy = @(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool.dll') -or
            ($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME')
        })
        if ($busy.Count -eq 0) { return }
        Start-Sleep -Seconds 5
    }
}
$buildResults = @()
foreach ($target in @('FPSGAMEEditor','FPSGAME')) {
    Write-Output "Waiting for existing engine work before $target."
    Wait-FreeBuild
    $log = Join-Path $receiptDir "$target-build-01.log"
    $output = Join-Path $receiptDir "$target-build-01-output.log"
    $started = Get-Date
    & 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' $target Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 "-Log=$log" *> $output
    $result = $LASTEXITCODE
    $buildResults += [ordered]@{ target=$target; exit_code=$result; started_at=$started.ToString('o'); finished_at=(Get-Date).ToString('o'); log=$log; output=$output }
    [ordered]@{ builds=$buildResults; runtime_tested=$false; editor_launched=$false } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $receiptDir 'build-receipt.json') -Encoding utf8
    Get-Content -LiteralPath $output -Tail 15
    if ($result -ne 0) { exit $result }
}
