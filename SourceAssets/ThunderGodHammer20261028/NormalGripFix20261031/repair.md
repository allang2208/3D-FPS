# 雷神之锤：静电场 / 线圈普通攻击左手接触修复

2026-10-31，用户要求排查并修复普通攻击左手脱离。

实际安装资产为 SteelWarhammer/NormalComboV4 的三段普通攻击及三段命中恢复，包含后续 BareSkin 手臂修正；不能只根据旧 Blender 文件覆盖动画。两款新握柄与原厂接口、中心线和握持直径一致。压缩误差较小；源动作在快速旋转帧中，左掌相对握柄的接触关系发生漂移，完整采样最大约 15.07 mm。第二段预备期间另有明确的主动松手换握，不能将其误判为接触错误。

修复为独立 UWeaponGripProfile，加载条件仅限雷神之锤装备 static_field_grip 或 coil_grip。沿现有动作的锤柄轴约束左掌接触点，以完整左臂链重新求解腕、肘和必要的锁骨支撑。保留原指骨局部曲线、武器/右手轨迹、时长、伤害时钟，以及主动换手阶段。高伸展姿态不比原动作进一步伸直。恢复片段使用相同的接触定义。

生产数据在原源帧之间额外采样，以减少快速挥击帧间的偏差；运行时复用已有的稀疏握持层，没有新增每帧 IK。新 profile 同时保留旧 clearance profile 的六个条目。

## 已落盘

- 源码：Source/FPSGAME/Production/ProductionToolComponent.cpp，仅增加两款握柄的 profile 选择。
- 资产：/Game/Weapons/ThunderGodHammer20261028/NormalGripFix20261031/DA_ThunderHammer_ConductiveGrip。
- 可编辑修正数据：contact_layer_editable.json；作者脚本 author_contact.py。
- 引擎保存回执：contact_receipt.json。
- 构建回执：build_receipt.json，FPSGAMEEditor Win64 Development 成功；DLL 包含新 profile 路径。

## 本次定向检查

check_saved_contact.py 读取已保存的 profile，并按现有运行时层的组合顺序应用于压缩后的原动画。检查涵盖三段普攻及三段命中收势，包括原源帧四分之一间隔的帧间采样。

结果见 saved_contact_check.json：握持阶段最大接触误差由约 15.07 mm 降至约 0.36 mm；骨段长度、武器/右手轨迹及明确松手阶段的偏差均在数值误差范围内。第一轮检查发现帧间残差后加密采样，最终回执 passed=true。

没有启动 UE 图形编辑器、PIE 或游戏，没有进行游戏内视觉验收。用户需在静电场、线圈两种装备下实测单击、连续三段攻击及命中后的收势。
