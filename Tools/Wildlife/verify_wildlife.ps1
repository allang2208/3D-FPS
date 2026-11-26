<#
.SYNOPSIS
  读回野外动物的动画集与角色蓝图，输出证据报告（不启动关卡、不进游戏）。
#>
param([ValidateRange(1, 3600)][int]$QueueWaitSeconds = 300)
$ErrorActionPreference = 'Stop'
$project = 'D:/FPS3D/FPSGAME'
$engine = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$outRoot = "$project/SourceAssets/Wildlife20261022"
$log = "$outRoot/wildlife-verify.log"
New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw '另一个 UE 制作批次仍占用桥接端口；本次未启动 commandlet。' }
    & $engine "$project/FPSGAME.uproject" -run=pythonscript "-script=$project/Tools/Wildlife/verify_wildlife_assets.py" `
        -NullRHI -unattended -nop4 -nosplash -nosound "-abslog=$log" *> "$outRoot/wildlife-verify-console.txt"
    if ($LASTEXITCODE -ne 0) { throw "读回校验失败；见 $log" }
    Write-Output 'WILDLIFE_VERIFY_COMPLETE'
}
finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
