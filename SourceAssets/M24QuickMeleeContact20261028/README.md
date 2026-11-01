# M24 枪托近战：右手换握与接触修订（2026-10-28）

用户要求出手时改成类似持棍的包握。原动作保持射击握姿转枪，击中帧右前臂进入枪托；本版重做右手换握、五指接触及腕肘支撑。

## 制作内容

- 先张指松开后握把，右手从枪体外侧绕到枪托下方；四指和拇指分别按实际枪托表面拟合，再包握挥击。
- 击中阶段握点固定在枪托局部空间，肩肘随后解算，保持原生骨长并由前臂辅助骨承接旋转。
- 回收时先松开包握，沿外侧路径返回射击握姿，0.72 秒完成右手回握；0.9 秒动作结束。
- 保留原枪体、左手、枪托接触标记及 0.25 秒击中时刻。普通弹匣与十发扩容弹匣同步更新，仅合并各 Profile 的 quick_melee 条目。
- 前送和回弹镜头曲线加重；命中时按强度叠加其他步枪共用的衰减抖动。M24 系数为 0.34，挥空没有碰撞冲击；撞到实体障碍产生反馈。伤害、耐力、冷却不变。

## 生产与落盘

- 当前可编辑母版：`M24_ClubGrip_Editable.blend`，包含两个 120 Hz / 109 帧动作。
- 握持拟合：`fit_club_surface.py` → `club_surface_fit.json`。
- 换握路径拟合：`fit_transition.py` → `transition_fit.json`。
- 动作生产：`author_regrip.py` → `final_poses.json`、`quick_melee_patch.json`、Blender 母版。
- 保存入口：`run_assets.ps1 -Stage install`。使用 UE 批次互斥和后台 commandlet，保存了 `/Game/Weapons/M24/MotionPolish20261027/DA_M24_SupportGrip` 与 `DA_M24_Mag10`，见 `install_receipt.json`。
- 原资产和导入前实时数据在 `Backups/`；导入只替换近战，保留此前换弹丢匣、拉栓、装备、冲刺和其他条目。
- 镜头源码：`Source/FPSGAME/Weapons/M24QuickMeleeMotion.h`、`Source/FPSGAME/Skills/FPSQuickCombatComponent.cpp`。完整 `FPSGAMEEditor` DLL 已成功构建，见 `build-receipt.json`。

## 本轮定向检查与边界

用户已要求排查穿模。本轮使用当前 V9 手臂、真实蒙皮与姿态修形，查看第一人称和手部近景，并对换握、回握连续采样；没有运行 UE 游戏或 PIE。

- 原击中帧前臂进入枪托约 22.51 mm。新版击中帧及已检查的换握、回握采样中，枪托区域未检出手掌或前臂内部顶点。
- 连续采样已消除中途厘米级的手指扫入。皮肤接触边缘仍有少量毫米级重叠，所测过渡帧最大约 2.54 mm；不将表面采样结果表述为全程零穿模。
- `grip_surface.json` 为握稳阶段记录；`transition_surface.json` 为最终换握、回握采样记录。`before_geometry.json` / `after_geometry.json` 的最近面法向代理不能作为实体穿透深度结论。
- `M24_ClubRegrip_Preview.gif` 为 0.5 倍速离线源动作预览，右侧有手部近景，不包含 UE 材质、实际 FOV 混合或运行时镜头冲击。
- 实际保存回读见 `readback_receipt.json`。最终游戏视角、手感与联机效果仍由用户测试。

## 输入保留

本制作仍引用 `M24ReloadFlow20261028` 的最新母版，以及 `M24ArmRebuild20261027`、`M24Hold20261027`、`M24LeftElbowReview20261028` 的骨架、相机校准和修形定义；这些输入仍是当前生产依赖。
