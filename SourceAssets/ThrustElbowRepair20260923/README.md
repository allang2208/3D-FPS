# Thrust elbow support V1

2026-09-23：标准柄、长柄两套正式 Thrust 已保存。保留手剑握持和肩肘腕位置，分配肘部与前臂旋转，锁住肩侧开口与腕侧支撑。只完成针对性离线蒙皮对比，未运行游戏测试。

制作方法、正式路径及边界见 [修复记录](../../Docs/Weapons/thrust-elbow-repair-20260923.md)。

## 重建输入

保留 `../MeleeArmOpening20260923/{Standard,LongGrip}/source.json`、`geometry.json`、`SourceArms.fbx`、`Thrust_patch.json` 与 V1 保存回执；本目录还读取 `../RuneSwordPickaxeOverhead20260920/ImpactV2/authoring.json` 的实际蒙皮站位。它们包含授权网格或密集骨架采样，Git 不提供这些本机输入。

`diagnose_elbows.py` 的直接执行入口属于修正前归因阶段，会要求盘上资产匹配 V1 哈希；修正落盘后不要恢复旧资产仅为重跑它。其矩阵与层级函数仍供作者脚本使用，现有 `diagnosis.json` 是本轮冻结输入。

Blender 后台制作入口为 `author_repair.py`，完整可编辑源由 `build_editable.py` 保存。`render_compare.py`、`inspect_transition.py` 只在用户要求相应诊断时运行。

`install_repair.py` 会检查源目标哈希，写入 14 条补偿轨道、完成压缩、导出 FBX、保存正式包与回执。`install_background.ps1` 仅适用于没有交互编辑器的后台接入；现有编辑器通过项目 MCP 批次桥执行 Python 脚本。重复运行安装不应绕过哈希检查覆盖较新修改。

完整 `.blend`、FBX、`.uasset`、`Before/` 备份、采样、图像、日志与回执保留本机。本机恢复清单与废案归档见 [发布记录](../../Docs/Weapons/melee-arm-publication-20260923.md)。
