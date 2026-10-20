param([int]$MaxWaitMinutes = 240)
# V9 R2 (pinhole fix): restore the V8 package saved in Before/, reinstall from the current payload, read back,
# then build Editor and Game. Refuses if the live viewmodel is not exactly our first V9 install.
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot; $project = [IO.Path]::GetFullPath((Join-Path $here '../..'))
$live = Join-Path $project 'Content/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416.uasset'
$before = Join-Path $here 'Before/Content/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416.uasset'
$deadline = (Get-Date).AddMinutes($MaxWaitMinutes)
function Wait-Idle {
    $said = $false
    while ($true) {
        $busy = @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe','UnrealEditor-Cmd.exe','UnrealEditor.exe','FPSGAME.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
        if (-not $busy.Count) { return }
        if ((Get-Date) -gt $deadline) { throw 'Other UE work stayed active past the wait limit; nothing changed.' }
        if (-not $said) { Write-Output ('Waiting for other UE work: ' + (($busy | ForEach-Object Name) -join ', ')); $said = $true }
        Start-Sleep -Seconds 20
    }
}
$receipt = Get-Content (Join-Path $here 'install_receipt.json') -Raw | ConvertFrom-Json
Wait-Idle
if ((Get-FileHash $live).Hash.ToLower() -ne $receipt.mesh_sha256) { throw 'Viewmodel changed since the first V9 install; preserved, nothing written.' }
Copy-Item (Join-Path $here 'install_receipt.json') (Join-Path $here 'install_receipt_r1.json') -Force
Copy-Item $before $live -Force
$start = Get-Date
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here 'run_ue.ps1') -ScriptName install_m4.py
$log = Get-ChildItem $here -Filter 'commandlet-2*.log' | Where-Object { $_.LastWriteTime -ge $start } | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $log -or -not (Select-String -Path $log.FullName -Pattern 'M4V9_INSTALL_COMPLETE' -Quiet)) {
    throw "Install did not complete (V8 package is in place; see $($log.FullName))"
}
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here 'run_ue.ps1') -ScriptName read_saved.py
foreach ($target in 'FPSGAMEEditor', 'FPSGAME') {
    Wait-Idle
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here 'build_native.ps1') -Targets $target
    if ($LASTEXITCODE -ne 0) { throw "$target build failed" }
}
Write-Output 'M4V9_R2_COMPLETE'
