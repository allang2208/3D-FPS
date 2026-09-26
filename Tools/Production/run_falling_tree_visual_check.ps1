# 树倒伏视觉只读体检运行器（2026-09-25，2026-09-26 修输出通道）。
# 只读：不修改、不保存任何资产；开始前确认没有 FPSGAME 编辑器/commandlet 占用。
# 用法：powershell -NoProfile -File Tools/Production/run_falling_tree_visual_check.ps1
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$engineCmd = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$pyScript = Join-Path $PSScriptRoot 'inspect_falling_tree_visual.py'
$projFile = Join-Path $project 'FPSGAME.uproject'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$outDir = Join-Path $project 'Saved/ProductionTreeHealth'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$stdoutLog = Join-Path $outDir "falling-visual-stdout-$stamp.txt"
$engineLog = Join-Path $outDir "falling-visual-engine-$stamp.log"
$reportLog = Join-Path $outDir "falling-visual-report-$stamp.txt"

# ---- 前置：项目互斥体空闲 -----------------------------------------------------
$busy = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" -ErrorAction SilentlyContinue |
    Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match [regex]::Escape('FPSGAME.uproject') })
if ($busy.Count -gt 0) {
    Write-Host "跳过：FPSGAME 编辑器/commandlet 正在运行（PID $($busy.ProcessId -join ',')）。本脚本不结束任何进程。" -ForegroundColor Yellow
    exit 2
}
if (-not (Test-Path $engineCmd)) { Write-Host "跳过：未找到 $engineCmd" -ForegroundColor Yellow; exit 2 }

Write-Host "只读体检开始（绝对路径调用）：$(Get-Date -Format 'HH:mm:ss')"
# 两条实测踩过的坑（2026-09-26）：
# 1) 必须写成 ("-script=" + 路径)。直接写 -script=$pyScript 时 PowerShell 5.1 不展开变量，
#    引擎收到字面量并把它当 Python 代码执行，报 `SyntaxError: invalid syntax (<string>, line 1)`。
# 2) Python 的 u.log()/print() 只写引擎日志文件，**不进 -stdout 捕获**，所以必须用 -abslog
#    指定本轮的日志文件，再从该文件里提取 FALLINGVIS 行（否则会误判成"脚本没输出"）。
& $engineCmd $projFile -run=pythonscript ("-script=" + $pyScript) -nullrhi -unattended -nosplash -stdout ("-abslog=" + $engineLog) *> $stdoutLog
$code = $LASTEXITCODE
Write-Host "引擎退出码 $code；stdout $stdoutLog；引擎日志 $engineLog"

$text = ''
foreach ($candidate in @($engineLog, $stdoutLog)) {
    if (Test-Path $candidate) { $text += (Get-Content $candidate -Raw) }
}
$lines = @([regex]::Matches($text, 'FALLINGVIS [^\r\n]*') | ForEach-Object { $_.Value.Trim() })
$lines | Set-Content -LiteralPath $reportLog -Encoding utf8
Write-Host "FALLINGVIS 行数：$($lines.Count) → $reportLog"

if ($text -match 'Project file not found|Could not find a valid project file|Failed to open descriptor file') {
    Write-Host "警告：引擎没能加载工程（Project file not found）" -ForegroundColor Red
}
if ($text -match 'FALLINGVIS DONE') { Write-Host '体检脚本跑完（FALLINGVIS DONE）' -ForegroundColor Green }
else { Write-Host '警告：没有看到 FALLINGVIS DONE 标记' -ForegroundColor Yellow }
if ($text -match 'Python script executed with errors') { Write-Host '警告：Python 脚本报错，见引擎日志' -ForegroundColor Red }

# ---- 摘要：只打印关键判据 -----------------------------------------------------
Write-Host ''
Write-Host '— 摘要 —'
$lines | Where-Object { $_ -match 'FALLINGVIS (ASSEMBLY |NANITE|MESH_SLOT |MESH_STATS|EXPR |PARAM |EXPR_ERR|PARAM_ERR|DONE)' } |
    ForEach-Object { Write-Host $_ }
exit 0