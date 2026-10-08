param([Parameter(Mandatory=$true)][string]$Script,[Parameter(Mandatory=$true)][string]$LogName,[switch]$Gpu)
$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$held=$true}
    if (-not $held) {throw 'UE asset queue timed out.'}
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'An editor is open; use the editor bridge.'}
    $scriptPath=Join-Path $PSScriptRoot $Script
    $logPath=Join-Path $PSScriptRoot ($LogName+'.log')
    $consolePath=Join-Path $PSScriptRoot ($LogName+'-console.log')
    $taskArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-run=pythonscript',"-script=$scriptPath",'-unattended','-nop4','-nosplash','-nosound',"-abslog=$logPath")
    if ($Gpu) {$taskArgs+=@('-AllowCommandletRendering','-RenderOffscreen')} else {$taskArgs+='-NullRHI'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @taskArgs *> $consolePath
    if ($LASTEXITCODE -ne 0) {throw "Blade texture operation failed: $logPath"}
    Write-Output "XUANCHI_TEXTURE_OPERATION_COMPLETE $Script"
} finally {
    if ($held) {$gate.ReleaseMutex()};$gate.Dispose()
}
