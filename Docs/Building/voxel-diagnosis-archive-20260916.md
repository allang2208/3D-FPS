# 退役文件归档 · VoxelDiagnosis20260916（2026-09-16）

按 WORKFLOW §4（退役文件放 `trash/<task>/` 并记录原路径、目标、大小、SHA-256、原因与保留替代物）与 §5（`trash` 不进 Git，公开文字清单放 `Docs/`）归档。

## 原路径与目标

- 原路径：`Intermediate/VoxelDiagnosis/`（未入 Git 的临时诊断目录）
- 目标：`trash/VoxelDiagnosis20260916/`
- 退役原因：这批脚本/输出是**一次性承重排查**用的工具与日志。结论已经写进 [垂直建造卡 1 m 排查](voxel-vertical-build-diagnosis-20260916.md)、[体素建造工作流](voxel-build-workflow.md)（含离线缩放基线数字）与 [建筑系统验收](voxel-build-audit-20260916.md)；保留在 `Intermediate/` 会让后续会话误以为它们是常驻工具，也会随构建目录被清理。
- 保留替代物：常驻的官方工具仍是 `Tools/Building/run_voxel_stress_probe.ps1`（材质强度与净跨契约）、`Tools/Building/read_voxel_save.py`（读档）、`Tools/Building/audit_voxel_placement.py`（无头放置判定）、以及本次新增的游戏内 `-VoxelBuildAudit`。需要重新做离线复现时，可按排查文档里的步骤从 `read_voxel_save.py` 的 `Reader` 重新生成 `cells.txt` 并复用 `scenario_probe.cpp`（已随本目录归档）。

## 清单（字节 / SHA-256 前 16 位）

| 文件 | 字节 | SHA-256 | 用途 |
| --- | --- | --- | --- |
| dump_cells.py | 4750 | 832D601E8506B27C | 把 `.sav` 导出成 cells.txt + 层位图/损伤/断键 |
| scenario_probe.cpp | 22312 | 2AF45A62BED9294D | 离线复算同一存档的接缝占比（含 `--bench` 缩放基线） |
| build_scenario_probe.ps1 | 1501 | C1CA7D72B2800ACA | 编译并运行上面的探针 |
| build.cmd / bench.cmd | 534 / 431 | 2242361B5B368C2F / 5CADCA43066269CD | 探针编译的中间批处理 |
| cells.txt / cells-old.txt / cells-nodamage.txt | 1236 / 2850 / 2862 | 113C111D5EC5B67C / ED16679584B0AA79 / B3F10A495A807843 | 存档导出的格表（当前 48 格 / 塌前 113 格 / 清零损伤版） |
| probe-out.txt / probe-out2.txt / probe-out3.txt | 55030 / 55070 / 69212 | ACB171CD033445B7 / 3C6CA07C80918FE8 / 7628BBE2B17118C5 | 场景 A–L 的复算输出 |
| probe-load.txt / probe-load2.txt / probe-nodamage.txt / probe-after.txt | 68944 / 75006 / 68958 / 61846 | 1EACF1DF244DA3A9 / 3C7881299CEA76FA / C9B25492D2D04586 / 3C8DB221A8C1D500 | 残骸荷载、抗剪改动前后、损伤清零前后的对比输出 |
| scenario_probe.exe / scenario_probe.obj | 90624 / 749189 | A25D835FE9443C6F / 3DF41B961C54C7A4 | 编译产物，可重新生成 |

## 恢复方式

把本目录文件移回 `Intermediate/VoxelDiagnosis/` 即可继续使用；`cells*.txt` 与 `probe-*.txt` 是当时的输入与输出快照，可用于复核结论。探针依赖 `Source/ThirdParty/Blast/Lib/Win64/FPSBlast.lib`，编译前先确认 Blast 已构建（`python Tools/Building/build_blast.py`）。
