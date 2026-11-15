<#
.SYNOPSIS
  后台创建野外动物的动画副本、动画数据集和角色蓝图（不启动编辑器界面、不进游戏）。

.DESCRIPTION
  读取 /Game/AnimalVarietyPack 的五套源资产，在 /Game/Monsters/Wildlife 下生成：
    <Species>/Animations/A_WL_<Species>_<Slot>   标准动作槽副本（关闭 Root Motion）
    <Species>/DA_WL_<Species>_AnimationSet       动作映射与走跑标称速度
    <Species>/BP_WL_<Species>                    父类 AColdSteelAnimal，已填物种 ID
  结果清单写入 SourceAssets/Wildlife20261022/authoring_manifest.json。
  已存在的资源不会被覆盖，可安全重跑。

.EXAMPLE
  powershell -NoProfile -File Tools/Wildlife/install_wildlife.ps1
#>
param([ValidateRange(1, 3600)][int]$QueueWaitSeconds = 300)
$ErrorActionPreference = 'Stop'
$project = 'D:/FPS3D/FPSGAME'
$engine = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$outRoot = "$project/SourceAssets/Wildlife20261022"
$log = "$outRoot/wildlife-authoring.log"
New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw '另一个 UE 制作批次仍占用桥接端口；本次未启动 commandlet。' }
    & $engine "$project/FPSGAME.uproject" -run=pythonscript "-script=$project/Tools/Wildlife/create_wildlife_assets.py" `
        -NullRHI -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$log" *> "$outRoot/wildlife-authoring-console.txt"
    if ($LASTEXITCODE -ne 0) { throw "野外动物资源制作失败；见 $log" }
    Write-Output 'WILDLIFE_AUTHORING_COMPLETE'
}
finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
