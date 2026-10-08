param([string]$Attempt='01',[switch]$ArchiveFailedPIEImport)
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$held=$true}
    if (-not $held) {throw 'UE asset queue timed out.'}
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'An editor is open; use the existing editor bridge.'}
    if ($ArchiveFailedPIEImport) {
        $meshRoot=[IO.Path]::GetFullPath('D:/FPS3D/FPSGAME/Content/Weapons/XuanChiZhenYue20261004/BladeV3/Meshes')
        $failedRoot=[IO.Path]::GetFullPath((Join-Path $taskRoot 'Before/FailedPIEImport'))
        [IO.Directory]::CreateDirectory($failedRoot) | Out-Null
        foreach ($meshName in @('SM_XuanChi_Blade_V3','SM_XuanChi_Guard_V3','SM_XuanChi_Complete_V3')) {
            foreach ($extension in @('.uasset','.uexp','.ubulk')) {
                $failedPath=[IO.Path]::GetFullPath((Join-Path $meshRoot ($meshName+$extension)))
                $savedPath=[IO.Path]::GetFullPath((Join-Path $failedRoot ($meshName+$extension)))
                if (-not $failedPath.StartsWith($meshRoot+[IO.Path]::DirectorySeparatorChar) -or -not $savedPath.StartsWith($failedRoot+[IO.Path]::DirectorySeparatorChar)) {throw 'Failed import archive path is outside its scoped directory.'}
                if (Test-Path -LiteralPath $failedPath) {Move-Item -LiteralPath $failedPath -Destination $savedPath -ErrorAction Stop}
            }
        }
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$taskRoot/install_assets.py" '-ExecCmds=Interchange.FeatureFlags.Import.FBX 0' -NullRHI -unattended -nop4 -nosplash -nosound "-abslog=$taskRoot/import-commandlet-$Attempt.log" *> "$taskRoot/import-console-$Attempt.log"
    if ($LASTEXITCODE -ne 0) {throw "BladeV3 import failed. See import-commandlet-$Attempt.log."}
    Write-Output 'XUANCHI_BLADE_V3_SAVED'
} finally {
    if ($held) {$gate.ReleaseMutex()};$gate.Dispose()
}
