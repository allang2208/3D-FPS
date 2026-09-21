<#
.SYNOPSIS
  检查点 B：把体素建造修复的「正式编译 → 探针回归 → 放置判定回归」三步一次跑完。

.DESCRIPTION
  对应 Docs/Building/voxel-build-fix-plan-20260921.md 的检查点 B。
  三步都**要求 FPSGAME 编辑器已关闭**：
    * Build-Editor.ps1 自身会在检测到编辑器进程时 throw；
    * UnrealEditor-Cmd（放置审计）需要项目互斥体，编辑器占用时会在引擎初始化阶段直接退出、
      连日志都不写（工作流第 6 节第 5 条）。
  所以本脚本先做前置检查，编辑器还开着就直接退出，不做任何事。

  探针的硬判据：跨度表必须与 Docs/Building/voxel-build-workflow.md 第 2 节一致 ——
    wood          自重 8.80 m / 跨中站 100 kg 6.80 m
    stone·marble  自重 7.80 m / 跨中站 100 kg 7.40 m

.EXAMPLE
  powershell -NoProfile -File Tools/Building/run-checkpoint-b.ps1
#>
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $project

function Fail($msg) { Write-Host "检查点 B 中止：$msg" -ForegroundColor Red; exit 1 }

# ---- 0. 前置：编辑器必须已关闭 -------------------------------------------------
$editors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" -ErrorAction SilentlyContinue |
    Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match [regex]::Escape('FPSGAME.uproject') })
if ($editors.Count -gt 0) {
    Fail "FPSGAME 编辑器仍在运行（PID $($editors.ProcessId -join ',')）。本脚本不结束任何进程，请先手动关闭。"
}
Write-Host "[0/3] 编辑器未运行，前置检查通过" -ForegroundColor Green

# ---- 1. 正式编译（可链接产物） -------------------------------------------------
Write-Host "[1/3] 全量编译 FPSGAMEEditor ..." -ForegroundColor Cyan
& powershell -NoProfile -File (Join-Path $PSScriptRoot '../Build/Build-Editor.ps1')
if ($LASTEXITCODE -ne 0) {
    # 审计友好化（2026-09-21）：本仓库常有并行会话在改源码，而未跟踪的新 .cpp 会被 UBT
    # 用 `git status` 的工作集排进构建 —— 它的语法错误会让**整个模块**失败，与本计划的改动无关。
    # 这里直接把"错误落在哪些文件"打出来，省得每次人工翻日志。
    $log = Get-ChildItem (Join-Path $project 'Saved/BuildEditor') -Filter '*.log' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($log) {
        $errLines = @(Select-String -Path $log.FullName -Pattern ': (error|fatal error) ' | ForEach-Object { $_.Line.Trim() })
        if ($errLines.Count -gt 0) {
            $files = @($errLines | ForEach-Object { if ($_ -match '^([^(]+)\(') { $Matches[1] } } | Sort-Object -Unique)
            $inBuilding = @($files | Where-Object { $_ -match '\\Building\\' })
            Write-Host "      错误总数 $($errLines.Count)，涉及文件：" -ForegroundColor Yellow
            $files | ForEach-Object { Write-Host "        - $_" -ForegroundColor Yellow }
            if ($inBuilding.Count -eq 0) {
                Write-Host "      ★ 这些错误**没有一个**落在 Source/FPSGAME/Building/ 下 ——" -ForegroundColor Yellow
                Write-Host "        很可能是并行会话正在编辑的文件让整个模块编译失败，请先让它停止变动。" -ForegroundColor Yellow
            } else {
                Write-Host "      ★ 有错误落在 Building/ 下，这才是本计划需要处理的：" -ForegroundColor Red
                $inBuilding | ForEach-Object { Write-Host "        - $_" -ForegroundColor Red }
            }
            Write-Host "      完整日志：$($log.FullName)" -ForegroundColor Gray
        }
    }
    Fail "Build-Editor.ps1 退出码 $LASTEXITCODE。"
}
Write-Host "[1/3] 编译成功" -ForegroundColor Green

# ---- 2. 探针：跨度表必须与文档一致 --------------------------------------------
Write-Host "[2/3] 离线承重探针 ..." -ForegroundColor Cyan
$probeOut = & powershell -NoProfile -File (Join-Path $PSScriptRoot 'run_voxel_stress_probe.ps1') 2>&1
$probeText = ($probeOut | Out-String)
$probeLog = Join-Path $project 'Saved/BuildingFixBackup/probe-checkpoint-b.txt'
New-Item -ItemType Directory -Force -Path (Split-Path $probeLog) | Out-Null
$probeText | Set-Content -LiteralPath $probeLog -Encoding utf8

# 期望：每种材质的 extended scan 行
$expect = @{
    'wood'          = @{ self = '8.80'; loaded = '6.80' }
    'stone'         = @{ self = '7.80'; loaded = '7.40' }
    'marble'        = @{ self = '7.80'; loaded = '7.40' }
}
$bad = @()
foreach ($mat in $expect.Keys) {
    # 抓到形如： extended scan (up to 10 m): self=8.80 m   with 100kg mid-span=6.80 m
    $m = [regex]::Match($probeText, "=== $mat\s.*?extended scan[^:]*:\s*self=([\d.]+) m\s+with 100kg mid-span=([\d.]+) m", 'Singleline')
    if (-not $m.Success) { $bad += "$mat（未匹配到 extended scan 行）"; continue }
    $self = $m.Groups[1].Value; $loaded = $m.Groups[2].Value
    if ($self -ne $expect[$mat].self -or $loaded -ne $expect[$mat].loaded) {
        $bad += "$mat 期望 self=$($expect[$mat].self)/loaded=$($expect[$mat].loaded)，实得 self=$self/loaded=$loaded"
    } else {
        Write-Host "      $mat : self=$self m  +100kg=$loaded m  OK" -ForegroundColor Green
    }
}
if ($bad.Count -gt 0) {
    Fail ("跨度表与文档不一致（硬判据失败）：`n      - " + ($bad -join "`n      - ") +
          "`n      探针完整输出：$probeLog`n      " +
          "若只有 wood 不一致，注意文档曾长期误写 0.09/0.23，已于 2026-09-21 更正为 0.050/0.231。")
}
Write-Host "[2/3] 跨度表逐项一致" -ForegroundColor Green

# ---- 3. 放置判定回归 ----------------------------------------------------------
Write-Host "[3/3] 放置判定无头审计 ..." -ForegroundColor Cyan
$engineCmd = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
if (-not (Test-Path $engineCmd)) {
    Write-Host "[3/3] 跳过：未找到 $engineCmd（放置审计不是硬判据，可手动运行 Tools/Building/audit_voxel_placement.py）" -ForegroundColor Yellow
} else {
    $auditLog = Join-Path $project 'Saved/BuildingFixBackup/placement-audit-checkpoint-b.log'
    # 必须用**绝对路径**：`& exe 'FPSGAME.uproject'` 由引擎按"当前工作目录"解析，而新进程的工作目录
    # 不保证是本工程目录 —— 实测会打印 `LogInit: Project file not found: FPSGAME.uproject` 后在
    # 初始化阶段静默退出（stdout 只有 4KB 启动日志、自定义 -log 文件 0 字节），看起来像"审计没输出"，
    # 实际根本没跑起来。脚本路径同样给绝对路径。
    $projFile = Join-Path $project 'FPSGAME.uproject'
    $auditScript = Join-Path $PSScriptRoot 'audit_voxel_placement.py'
    $stdoutLog = Join-Path $project 'Saved/BuildingFixBackup/placement-audit-stdout.txt'
    & $engineCmd $projFile -run=pythonscript -script=$auditScript -nullrhi -unattended -stdout *> $stdoutLog
    $auditText = if (Test-Path $stdoutLog) { Get-Content $stdoutLog -Raw } else { '' }
    $auditText | Set-Content -LiteralPath $auditLog -Encoding utf8 -ErrorAction SilentlyContinue
    # 启动期失败（找不到工程 / 互斥体被占等）给一条明确提示，避免误判成"审计无输出"。
    if ($auditText -match 'Project file not found|Could not find a valid project file|Failed to open descriptor file') {
        Write-Host "[3/3] 警告：引擎未能加载工程（日志出现 Project file not found）。stdout: $stdoutLog" -ForegroundColor Red
    }
    $layers = @([regex]::Matches($auditText, 'AUDIT layer z=\s*\d+.*'))
    if ($layers.Count -eq 0) {
        Write-Host "[3/3] 警告：审计没有输出 AUDIT layer 行，日志见 $auditLog（可能是互斥体或地图加载问题）" -ForegroundColor Yellow
    } else {
        $incomplete = @($layers | Where-Object { $_.Value -match 'INCOMPLETE' })
        Write-Host "      共 $($layers.Count) 层；INCOMPLETE 标记 $($incomplete.Count) 处" -ForegroundColor Cyan
        $layers | ForEach-Object { Write-Host "      $($_.Value.Trim())" }
        if ($incomplete.Count -gt 0) {
            Write-Host "[3/3] 注意：有层被标记 INCOMPLETE —— 这是审计脚本的正常检测输出，" -ForegroundColor Yellow
            Write-Host "      需与改动前的基线报告比对才能判断是否为回归。基线见 Docs/Building/voxel-build-audit-20260916.md。" -ForegroundColor Yellow
        } else {
            Write-Host "[3/3] 放置判定无 INCOMPLETE" -ForegroundColor Green
        }
    }
}

Write-Host ""
Write-Host "检查点 B 完成。产物：" -ForegroundColor Green
Write-Host "  探针输出     : Saved/BuildingFixBackup/probe-checkpoint-b.txt"
Write-Host "  放置审计日志 : Saved/BuildingFixBackup/placement-audit-checkpoint-b.log"
Write-Host "  编译日志     : Saved/BuildEditor/ 下最新 build-*.log"
Write-Host ""
Write-Host "接下来（检查点 C）需要你进游戏实测：倒塌碎块不再凭空消失（P20）、大建筑连续建造帧率（P2/P3/P18/P19）。"
