# 人形怪物眩晕摇晃

2026-09-26。接续用户选择的本地 Mesh2Motion `Dizzy` 动作，为护士、胖子、突变体 3、重建巫婆接入站立眩晕表现。保留现有模型、蒙皮、伤害公式与状态数值；没有运行测试、预览或性能采样。

## 控制与动画合同

- 只有 `UMonsterCombatComponent::ReceiveStun`、`UCombatStatusFormula::AddStun` 和现有弹反的明确眩晕使用摇晃表现。破韧属于硬直，不设置 `bStunned`。普通枪械、DOT 的免硬直闸门不变。
- 默认先保留 0.14 秒现有受击动作，随后用 0.16 秒姿态快照混合到 Dizzy。招架保留 0.45 秒原有回退/受击前段。
- 只有明确眩晕的剩余时长至少覆盖进入段加 0.3 秒时才启用摇晃；短眩晕保留原受击，不额外延长控制时长。
- Dizzy 按原反应更新推进，明确眩晕剩余约 0.22 秒时从当前姿态混合到动态 Idle。眩晕用世界游戏时间保存独立到期点，破韧不能延长眩晕；总体动作封锁仍取剩余控制的较大值，没有新增定时器或组件 Tick。
- 同一眩晕刷新可延长控制，保留摇晃进度。若正在恢复时追加眩晕，从当时姿态重新混合进摇晃。
- 冻结、石化期间保留原受控表现，不播摇晃；较长眩晕在上述状态解除后仍有时间时可以进入摇晃。通用打断不再缩短既有未到期控制。
- 击飞/倒地/起身由已有 Knockdown 组件接管；死亡优先级最高。受控期间原攻击伤害窗口不推进。
- 破韧硬直复用各自受击片段，快速冲击后连续采样卸力段，最后恢复；跳过胖子/突变体/巫婆源片段中静态保持段。硬直结束恢复动态 Idle，不停留在受击末帧。冻结、石化仍可定格，不能套用这套动态硬直采样。
- 护士速度 1、胖子 0.8、突变体 1.05、重建巫婆 0.9；组件 `DizzyClip` / `DizzyPlayRate` 可配置。旧巫婆骨架、非人形沿用原表现。

## 动作制作与路径

源：`SourceAssets/FatZombieMeshy20260913/sources/human-addon-animations.glb` 中 `Dizzy`，源时长 2.375 秒，60 fps FBX 导出区间约 2.3833 秒。Mesh2Motion 提交 `2d3d1ff03247d9e7e830d1ae375653da4e2146e2`，CC0-1.0。

沿用上轮四种人形的 IK 映射。在源动作基础上重建 Meshy 原绑定骨长，移除累计骨盆位移、闭合循环、双脚固定到作者支撑点，并保留胖子手部与躯干间距；不修改角色骨架和权重。

目标为 `/Game/Monsters/HumanoidStun/{Nurse,FatZombie,Mutant3,Witch}/A_{Role}_Dizzy`。源文件、Blender/FBX、许可和收据保存在 `SourceAssets/HumanoidStun20260926`。正式导入完成以 `fitted_delivery.json` 为记录，不能把准备好的脚本视为已保存资产。

后台制作脚本：

1. `Tools/HumanoidStun/export_source.py`：提取本地源动作。
2. `Tools/HumanoidStun/retarget_source.py`：导入源片段，复用既有 IK 映射并导出四种原始重定向输入。
3. `Tools/HumanoidKnockdown/fit_recovery.py -- --root D:/FPS3D/FPSGAME/SourceAssets/HumanoidStun20260926 --loop --plant-feet`：Blender 后台烘焙；不带这些参数时保留原击飞制作行为。
4. `Tools/HumanoidStun/import_fitted.py`：导入四种最终循环并保存。

## 性能与当前交付状态

纯动画采样，不调用刚体模拟，不占用布娃娃数量或刚体预算。复用现有反应更新；动作在角色初始化时加载，命中和每帧路径不重复加载资源。进入/退出仅保存一次姿态快照。状态组件引用在每次反应进入时刷新，播放中不逐帧扫描组件。沿用当前权威端执行方式，没有新增网络同步功能。

四种最终适配动作已通过后台 Python commandlet 导入并保存，记录见 `fitted_delivery.json` 与 `Saved/HumanoidStun-final-import.log`。首版眩晕接入的正式构建日志为 `Saved/BuildEditor/build-20260926-193229.log`；后续硬直/眩晕分离修订的状态见 `Docs/Monsters/stagger-stun-separation-20260926.md`，不能用首版构建代表后续修订。本任务没有关闭或重启编辑器、没有启动游戏或测试。动画效果、控制衔接与多怪性能仍交由用户测试。
