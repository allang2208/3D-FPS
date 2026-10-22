param(
    [ValidateRange(1, 3600)][int]$QueueWaitSeconds = 300,
    [switch]$VerifyOnly
)
$ErrorActionPreference = 'Stop'

$projectRoot = 'D:/FPS3D/FPSGAME'
$engine = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$outRoot = "$projectRoot/SourceAssets/PickaxeSkeletonRestore20261022"
$script = "$projectRoot/Tools/ProductionTools/restore_pickaxe_skeleton.py"
$verifyScript = "$projectRoot/Tools/ProductionTools/verify_pickaxe_skeleton.py"
$targetPackage = "$projectRoot/Content/Items/ProductionTools/GripMotion20260913/SK_Harvest_Pickaxe_Skeleton.uasset"

# Standard batch mutex used by the project's editor bridge.
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    if (-not (Test-Path -LiteralPath $engine)) { throw "Engine not found: $engine" }
    if (-not (Test-Path -LiteralPath $outRoot)) { New-Item -ItemType Directory -Path $outRoot -Force | Out-Null }

    # Never touch a project the editor currently owns.
    $editors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" |
        Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME\.uproject' })
    if ($editors.Count -gt 0) {
        throw 'A FPSGAME editor is running; close it before restoring the skeleton. No process was stopped.'
    }

    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) }
    catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw 'Another UE authoring batch holds the mutex; nothing was started.' }

    if ($VerifyOnly) {
        if (-not (Test-Path -LiteralPath $targetPackage)) { throw 'Target package does not exist; nothing to verify.' }
        & $engine "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$verifyScript" `
            -NullRHI -unattended -nop4 -nosplash -nosound `
            "-abslog=$outRoot/verify.log" *> "$outRoot/verify-console.txt"
        $code = $LASTEXITCODE
        if ($code -ne 0) { throw "Verification commandlet exited $code; see verify.log." }
        Write-Output 'PICKAXE_SKELETON_VERIFY_OK'
        return
    }

    if (Test-Path -LiteralPath $targetPackage) {
        throw 'SK_Harvest_Pickaxe_Skeleton.uasset already exists; this runner never overwrites. Use -VerifyOnly to inspect it.'
    }

    & $engine "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$script" `
        -NullRHI -unattended -nop4 -nosplash -nosound `
        "-abslog=$outRoot/restore.log" *> "$outRoot/restore-console.txt"
    $code = $LASTEXITCODE
    if ($code -ne 0) { throw "Restore commandlet exited $code; see restore.log." }

    $receipt = Join-Path $outRoot 'restore_receipt.json'
    if (-not (Test-Path -LiteralPath $receipt)) { throw 'Restore produced no receipt.' }
    $state = Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
    if ($state.stage -ne 'verified') {
        throw "Restore stage was '$($state.stage)'; errors: $($state.errors -join '; ')"
    }
    if (-not (Test-Path -LiteralPath $targetPackage)) {
        throw 'Receipt claims success but the package is not on disk.'
    }

    # Second process so the readback cannot come from a cached in-memory object.
    & $engine "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$verifyScript" `
        -NullRHI -unattended -nop4 -nosplash -nosound `
        "-abslog=$outRoot/verify.log" *> "$outRoot/verify-console.txt"
    $verifyCode = $LASTEXITCODE
    if ($verifyCode -ne 0) { throw "Fresh-process verification exited $verifyCode; see verify.log." }

    Write-Output 'PICKAXE_SKELETON_RESTORE_OK'
}
finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
