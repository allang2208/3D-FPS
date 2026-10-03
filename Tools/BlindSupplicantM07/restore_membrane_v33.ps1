$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME'
$taskAssets = "$taskRoot/SourceAssets/BlindSupplicantM07Meshy20261001"
$taskOut = "$taskAssets/RecoverMembraneV33"
$taskSource = "$taskAssets/MembraneStabilityV31/Before/SK_M07_BodyMotionV18.uasset"
$taskTarget = "$taskRoot/Content/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18.uasset"
$taskProcesses = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine.Replace('\','/').IndexOf("$taskRoot/FPSGAME.uproject",[StringComparison]::OrdinalIgnoreCase) -ge 0 })
if ($taskProcesses.Count) { throw 'FPSGAME has loaded packages; offline mesh restoration deferred.' }
New-Item -ItemType Directory -Path "$taskOut/Before" -Force | Out-Null
$taskBackup = "$taskOut/Before/SK_M07_BodyMotionV18_V31.uasset"
if (-not (Test-Path -LiteralPath $taskBackup)) { Copy-Item -LiteralPath $taskTarget -Destination $taskBackup }
Copy-Item -LiteralPath $taskSource -Destination $taskTarget -Force
$taskRecord = [ordered]@{
    revision='RecoverMembraneV33'; restored=$true; source=$taskSource; target=$taskTarget
    previous_version_backup=$taskBackup; restored_sha256=(Get-FileHash -LiteralPath $taskTarget -Algorithm SHA256).Hash
    restored_scope='Exact pre-V31 mesh package, including original cloth mapping, proxy data and configuration; current Blueprint not overwritten'
    blueprint_clearance_restore_pending=$true; runtime_tested=$false
}
$taskRecord | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$taskOut/membrane_package_restore_v33.json" -Encoding utf8
Write-Output 'M07_V33_PRE_V31_MESH_RESTORED'
