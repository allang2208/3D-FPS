# 原版 FPS 动画复用核对 — 2026-09-09

用户在 UE 手部修复后仍反馈明显扭曲，要求考虑现成 FPS 动画或完整复用 Godot 原版。本轮完成来源核对与现成资产检索；没有把本文方案冒称为已完成的新迁移，也没有购买资产。

## 当前 Godot 真正生效的资产

- `E:/3d/3-dfps/weapon_data/akm_classic.tres` → `scenes/weapons/akm_classic.tscn` → `assets/models/akm_classic/akm_refined_v2.glb`。
- `scripts/infima_viewmodel.gd` 默认开启 `fitted_hands_enabled`，通过 `scripts/fitted_player_hands.gd` 安装 `assets/models/player_hands/free_fitted_v1/akm_classic.res`。只看原 GLB 会漏掉正式手部网格。
- 完整可编辑复用源为 `E:/无尽轮回/3d/free-hands-20260908/editable-v6/akm_classic.glb` 和同名 `.blend`。GLB 为 41,756,264 字节，两个 skin：机械 12 骨、手部 68 骨，九段动作。保存重开记录在同目录 `editable-check.json`。
- 手模型来自 NadevayNoski 的 Realistic human hand model，许可和已获取源文件记录在 `E:/3d/3-dfps/assets/models/player_hands/free_fitted_v1/CREDITS.md`；不是 CC0。不得把 WRAD 许可证套到这套源资产上。

## 旧 UE 迁移偏差

`Tools/AssetPipeline/build_akm_ue.py` 读取旧 `E:/3d/akm-classic-staging/akm-classic-unified.blend`，报告中的手网格是 `SK_FP_CH_Default_Cubic.001`。它没有包含 Godot 的正式手网格替换。之后 WRAD 适配重复改变了手部 rest geometry 和权重。

UE 并非所有骨骼动画都从零制作：九个源 clip 已导入。后续又改造了单发动作、装备动作，并给换弹添加额外非线性时间映射。因此，仅宣称动画文件已导入不足以证明当前 Godot 效果被完整复用。

直接读取源 GLB 的动画时间后确认：

| 动作 | Godot 最终秒数 | UE 旧 staging 导出秒数 |
| --- | ---: | ---: |
| reload | 2.7 | 3.333333 |
| reload_empty | 3.466667 | 4.291667 |
| draw | 1.0 | 1.208333 |
| holster | 0.8 | 0.958333 |
| inspect | 5.0 | 6.208333 |
| fire / aim_fire | 0.866667 | 1.041667 |

Godot `.glb.import` 的采样率为 30；旧 staging 的 UE 导出使用 24。原 GLB 的 idle/aim 为 0.066667 秒；editable-v6 优化后保留单姿态零时刻键，因此静态 clip 时长应取原 GLB 元数据，不能误导入为零长度。

## 推荐复用方法

1. 先完整保留 Godot 正式的手部 mesh、Skin、绑定矩阵、骨架和动作曲线，只做坐标/单位/格式转换；不重新权重拟合。
2. 用最终原 GLB 的秒数作合同，取消旧 staging 造成的二次调速和额外换弹相位改造。
3. 同时复用运行时行为：`infima_viewmodel.gd` 的 ADS 混合、稳定单发、握持/配件修正、装备时从 empty_reload 1.75 秒开始并加 0.18 秒混入；`gun.gd` 的镜头、后坐、摆动和 ADS 对齐需要等效移植，不能由 FBX 自动包含。
4. 以相同时刻的骨骼姿态、手部变形、弹匣/拉栓接触和动作耗时对照 Godot。保持动作数据是可行目标；跨引擎像素完全相同不能预先保证。
5. 用户的 `D:/迅雷下载/akm.fbx` 可以继续作为枪械几何候选，但枪形改变意味着握把、弹匣、枪机与原手接触位置需要适配。先建立原枪+原手的基准，再替换枪械刚性零件，避免又改坏手的蒙皮。

已实际查看 `animation-v6-review/akm_classic-false-standard-reload.jpg` 与 `equip_charge.jpg`：Godot 原版近景本身也仍有掌心凹槽。完整复用可以恢复已有版本，不能自动消除源资产已有瑕疵。

## 现成 FPS 资产候选

- Fab FPS Animation Pack： https://www.fab.com/listings/8a75dec9-84f4-416e-9b08-8d03eb3bd844 。商品页列出 120+ 动作、七种武器（含 AK74U）、换弹/空仓换弹/装备/检视，以及枪口火焰和烟雾。付费候选；AK74U 不是当前 AKM，需先核实原配手模、目标 UE 版本和演示质量。
- Fab Animated AKM/AKMS： https://www.fab.com/listings/5b9b6d31-906f-4aae-a602-02bd03c8dae2 。商品页列出 34 段动作（24 角色、10 武器），含上膛、换弹、检视和冲刺。付费候选；第一人称手部包含范围与 UE 5.8 实际兼容性尚未验收。
- 免费无新增购买费用的首选是项目已经拥有的完整 Godot 资产。本轮没有核实到能原样套入当前 AKM、同时提供成熟原配手模/蒙皮/完整动作的免费 Fab 替代包。

成品路线应选原配手模、原骨架、原蒙皮与动画一起使用的完整组合。单独换一份动画不会自动修复当前手的蒙皮变形。
