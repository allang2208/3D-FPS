<#
.SYNOPSIS
  用项目自带的 Blast 适配器离线复算 20 cm 体素的连接强度（不启动编辑器、不进游戏）。

.DESCRIPTION
  数值平衡的验收入口：改过密度/抗拉/抗剪后必须跑一遍，确认每种材质都撑得住
  2.0 m 净跨（含跨中站 100 kg 玩家），并在约 3-4 m 前失效。

  判定公式与 Source/FPSGAME/Building/VoxelSupportGraph.cpp 的 VoxelStress::Solve 一致，
  并与游戏内浮窗共用 Source/FPSGAME/Building/VoxelJointStrength.h；本脚本只是把
  同一份代码编成一个命令行探针。

.EXAMPLE
  powershell -NoProfile -File Tools/Building/run_voxel_stress_probe.ps1
#>
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$blast = Join-Path $project 'Source/ThirdParty/Blast'
$out = Join-Path $project 'Intermediate/VoxelStressProbe'
New-Item -ItemType Directory -Force -Path $out | Out-Null

$vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
$install = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$vcvars = Join-Path $install 'VC/Auxiliary/Build/vcvars64.bat'
if (-not (Test-Path $vcvars)) { throw "vcvars64.bat not found: $vcvars" }

$source = Join-Path $PSScriptRoot 'voxel_stress_probe.cpp'
$library = Join-Path $blast 'Lib/Win64/FPSBlast.lib'
if (-not (Test-Path $library)) { throw "Build Blast first: python Tools/Building/build_blast.py" }
# VoxelJointStrength.h lives with the game code and is shared by both callers.
$includes = @(
    (Join-Path $blast 'Adapter'),
    (Join-Path $project 'Source/FPSGAME/Building')
) | ForEach-Object { '/I"' + $_ + '"' }

$batch = Join-Path $out 'build.cmd'
@"
@echo off
cd /d "$out"
call "$vcvars" >nul
cl /nologo /O2 /MD /EHsc /std:c++17 /DNDEBUG /DNVBLAST_STATIC /DNV_STATIC_LIB /D_CRT_SECURE_NO_WARNINGS $($includes -join ' ') "$source" /Fe:voxel_stress_probe.exe /link "$library"
"@ | Set-Content -LiteralPath $batch -Encoding ASCII

& cmd /d /c $batch
if ($LASTEXITCODE -ne 0) { throw "compile failed" }
& (Join-Path $out 'voxel_stress_probe.exe')
