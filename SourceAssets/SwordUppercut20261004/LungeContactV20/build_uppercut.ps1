param([string[]]$Targets = @('FPSGAME','FPSGAMEEditor'))
$ErrorActionPreference = 'Stop'
$uppercutProject = 'D:\FPS3D\FPSGAME'
$uppercutBatch = 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
$uppercutReceipts = @()
$uppercutReceiptPath = Join-Path $PSScriptRoot 'build_receipt.json'
if (Test-Path -LiteralPath $uppercutReceiptPath) { $uppercutReceipts = @(Get-Content -LiteralPath $uppercutReceiptPath -Raw | ConvertFrom-Json) }
foreach ($uppercutTarget in $Targets) {
    # Do not compete with an already-running compiler or link occupied editor DLLs.
    do {
        $uppercutBuilders = @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -match '^cl.exe$|^UnrealBuildTool.exe$|^link.exe$' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if ($uppercutBuilders.Count) { Wait-Process -Id $uppercutBuilders.ProcessId -Timeout 30 -ErrorAction SilentlyContinue }
    } while ($uppercutBuilders.Count)
    if ($uppercutTarget -eq 'FPSGAMEEditor') {
        # Resource commandlets use the Editor DLL too. Let their own work finish;
        # building the independent Game executable does not replace that DLL.
        do {
            $uppercutCommandlets = @(Get-CimInstance Win32_Process | Where-Object {
                $_.Name -eq 'UnrealEditor-Cmd.exe' -and
                ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')
            })
            if ($uppercutCommandlets.Count) {
                Wait-Process -Id $uppercutCommandlets.ProcessId -Timeout 30 -ErrorAction SilentlyContinue
            }
        } while ($uppercutCommandlets.Count)
        $uppercutEditors = @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq 'UnrealEditor.exe' -and
            ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')
        })
        if ($uppercutEditors.Count) { throw 'The project editor is running. No editor was stopped.' }
        do {
            $uppercutBuilders = @(Get-CimInstance Win32_Process | Where-Object {
                $_.Name -match '^cl.exe$|^UnrealBuildTool.exe$|^link.exe$' -or
                ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
            })
            if ($uppercutBuilders.Count) { Wait-Process -Id $uppercutBuilders.ProcessId -Timeout 30 -ErrorAction SilentlyContinue }
        } while ($uppercutBuilders.Count)
    }
    $uppercutLog = Join-Path $PSScriptRoot ('build-' + $uppercutTarget + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
    & $uppercutBatch $uppercutTarget Win64 Development "-Project=$uppercutProject\FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoLiveCoding "-Log=$uppercutLog"
    $uppercutExit = $LASTEXITCODE
    $uppercutReceipts = @($uppercutReceipts | Where-Object { $_.target -ne $uppercutTarget })
    $uppercutReceipts += [pscustomobject]@{target=$uppercutTarget;exit_code=$uppercutExit;log=$uppercutLog;tests_run=$false}
    ConvertTo-Json -InputObject $uppercutReceipts -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Encoding UTF8
    if ($uppercutExit -ne 0) { throw "Build failed: $uppercutTarget, exit $uppercutExit. See $uppercutLog" }
}
Write-Output ('Uppercut V20 requested native builds complete: ' + ($Targets -join ', ') + '. Runtime testing remains manual.')
