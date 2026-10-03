$ErrorActionPreference = 'Stop'
$uppercutProject = 'D:\FPS3D\FPSGAME'
$uppercutBatch = 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
$uppercutReceipts = @()
foreach ($uppercutTarget in @('FPSGAME','FPSGAMEEditor')) {
    # Do not compete with an already-running compiler or link occupied editor DLLs.
    $uppercutBuilders = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^cl.exe$|^UnrealBuildTool.exe$|^link.exe$' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if ($uppercutBuilders.Count) { throw 'Another native build is active. Preserve this build script for later execution.' }
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
        $uppercutBuilders = @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -match '^cl.exe$|^UnrealBuildTool.exe$|^link.exe$' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if ($uppercutBuilders.Count) { throw 'Another native build is active. Preserve this build script for later execution.' }
    }
    $uppercutLog = Join-Path $PSScriptRoot ('build-' + $uppercutTarget + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
    & $uppercutBatch $uppercutTarget Win64 Development "-Project=$uppercutProject\FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoLiveCoding "-Log=$uppercutLog"
    $uppercutExit = $LASTEXITCODE
    $uppercutReceipts += [pscustomobject]@{target=$uppercutTarget;exit_code=$uppercutExit;log=$uppercutLog;tests_run=$false}
    ConvertTo-Json -InputObject $uppercutReceipts -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Encoding UTF8
    if ($uppercutExit -ne 0) { throw "Build failed: $uppercutTarget, exit $uppercutExit. See $uppercutLog" }
}
Write-Output 'Uppercut V14 Game and Editor native builds complete. Runtime testing remains manual.'
