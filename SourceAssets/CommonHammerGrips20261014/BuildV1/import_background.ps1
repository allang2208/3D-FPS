param([switch]$FreshPackagesOnly,[switch]$MeshRevisionOnly)
$ErrorActionPreference = 'Stop'
$taskRoot = 'D:\FPS3D\FPSGAME\SourceAssets\CommonHammerGrips20261014\BuildV1'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne(60000) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw 'Asset batch is busy; import not started.' }
    $existing = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME' })
    if ($existing | Where-Object Name -eq 'UnrealEditor.exe') { throw 'Interactive editor active; use the existing bridge.' }
    if ($existing.Count -gt 0) {
        if (-not $FreshPackagesOnly) { throw 'Commandlet active; defer replacement imports.' }
        # Permit new packages or this batch's unpublished partial saves only.
        # No existing factory package is saved by import_grips.py.
        $taskOwnedPartial = @()
        $taskReceiptPath = Join-Path $taskRoot 'import_receipt.json'
        if (Test-Path -LiteralPath $taskReceiptPath) {
            $taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json
            if ($taskReceipt.complete -eq $false) {
                foreach ($taskAsset in $taskReceipt.assets) {
                    $taskOwnedPartial += (($taskAsset.Split('.')[0] -replace '^/Game/','')+'.uasset')
                }
            }
        }
        $taskPackages = @()
        $taskExport = Get-Content -LiteralPath (Join-Path $taskRoot 'exports.json') -Raw | ConvertFrom-Json
        foreach ($taskRow in $taskExport.parts) {
            $taskPackages += ('Weapons/CommonHammerGrips20261014/BuildV1/UV1/'+$taskRow.mesh+'.uasset')
            if (-not $MeshRevisionOnly) { $taskPackages += ('ColdSteelData/AttachmentIcons20260913/grip_'+$taskRow.id+'.uasset') }
        }
        if (-not $MeshRevisionOnly) {
        foreach ($taskMaterial in @('M_HammerGripWoven','M_HammerGripLeather','M_HammerGripDarkLeather')) {
            $taskPackages += ('Weapons/CommonHammerGrips20261014/BuildV1/Materials/'+$taskMaterial+'.uasset')
        }
        foreach ($taskKind in @('Woven','Leather')) { foreach ($taskChannel in @('BaseColor','Normal','ORM')) {
            $taskPackages += ('Weapons/CommonHammerGrips20261014/BuildV1/Textures/T_HammerGrip_'+$taskKind+'_'+$taskChannel+'.uasset')
        } }
        }
        foreach ($taskPackage in $taskPackages) {
            if ((Test-Path -LiteralPath (Join-Path 'D:\FPS3D\FPSGAME\Content' $taskPackage)) -and $taskPackage -notin $taskOwnedPartial) { throw ('Existing target package: '+$taskPackage) }
        }
    }
    $taskEditorBuild = Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object { $_.CommandLine -match 'UnrealBuildTool.*FPSGAMEEditor' }
    if ($taskEditorBuild) { throw 'Editor binary build active; defer commandlet launch.' }
    $taskImportName = if ($MeshRevisionOnly) { 'import_mesh_uv.py' } else { 'import_grips.py' }
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' -run=PythonScript "-script=$taskRoot\$taskImportName" -unattended -nop4 -nosplash -nosound -NullRHI "-abslog=$taskRoot\import-engine.log" *> "$taskRoot\import-console.log"
    $code = $LASTEXITCODE
    @{exit_code=$code;fresh_packages_only=[bool]$FreshPackagesOnly;game_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot\commandlet_receipt.json" -Encoding UTF8
    exit $code
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
