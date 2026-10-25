param([string]$ReceiptName=('quiver-audit-'+(Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference='Stop'
$quiverAuditProject='D:/FPS3D/FPSGAME'
$quiverAuditRoot=Join-Path $quiverAuditProject 'SourceAssets/LeatherQuiverBelt20261025/Audit20261025'
$quiverAuditReport=Join-Path $quiverAuditRoot $ReceiptName
[void](New-Item -ItemType Directory -Force -Path $quiverAuditReport)
$quiverAuditMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$quiverAuditHeld=$false
try {
    try {$quiverAuditHeld=$quiverAuditMutex.WaitOne()} catch [Threading.AbandonedMutexException] {$quiverAuditHeld=$true}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$quiverAuditProject/FPSGAME.uproject" '-run=BowSkillTrainingAudit' '-QuiverBelt' "-ReportDir=$quiverAuditReport" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' '-NoAssetRegistryCache' '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$quiverAuditReport/engine.log" *> "$quiverAuditReport/console.txt"
    $quiverAuditExit=$LASTEXITCODE
    Write-Output "Quiver audit exit=$quiverAuditExit; report=$quiverAuditReport/result.json"
    Select-String -LiteralPath "$quiverAuditReport/console.txt" -Pattern 'QUIVER_AUDIT.*FAIL|QUIVER_AUDIT_DONE|Fatal error|error C' | ForEach-Object {$_.Line}
    exit $quiverAuditExit
} finally {if($quiverAuditHeld){$quiverAuditMutex.ReleaseMutex()};$quiverAuditMutex.Dispose()}
