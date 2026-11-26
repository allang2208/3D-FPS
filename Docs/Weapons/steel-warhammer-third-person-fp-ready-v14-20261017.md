# 双手锤第三人称：参考第一人称握持 V14

2026-10-17。用户否定 V13 低位斜持的观感，明确要求参考第一人称握锤状态重新优化手和手臂。本轮以该新指令为准，恢复较高的胸前持锤准备姿态。

## 参考与适配

从当前 `items.json` 的 `ue_steel_warhammer` 定义解析第一人称网格和 Idle：`SprintDragV1/SK_Warhammer_BareArmsSprintV1`、`A_RusticPickaxe_Idle`。后台读取实际资源第 0 秒的肩、肘、腕、锤根及参考骨架，保存为 `FirstPersonReadyV14/first-person-hold.json`。读取动作属于制作输入，未启动游戏或渲染。

运行时普通 Idle 使用上述序列；Warhammer Clearance 姿态差量的制作输入为攻击/回收，不含 Idle。参考坐标按第一人称网格 yaw +90°、身体网格 yaw -90°转换，再取肩部相对的双手中点、各自肘位和完整锤柄朝向。手位接近肩部高度，肘部位于握点下方，区别于 V13 人工设定的肩下 28 cm 低位横抱。

按 Jason 实际臂长缩放肩部相对偏移，保留全身模型真实肩点和肩宽，不搬入第一人称为画框设置的肩部位置。双手继续约束在同一根刚性锤柄上，完整掌向和握距来自当前第一人称资源；用解剖肘平面与上下臂扭转辅助骨适配不同骨架。初始求解固定第一人称的握柄朝向，不再用沿柄大幅翻转的候选决定待机掌向。

V12 的居中身体、稳定头颈、呼吸、骨盆、腿部和八方向步态不变。第一人称转锤待机、检视、冲刺拖地和相机轨迹不接入；攻击时序与现成第三人称攻击素材不变。握持修订同步到站立、走跑及冲刺预备回退，避免状态切换时回到 V13 的低位姿态。

## 制作与保存

- 作者目录：`SourceAssets/WarhammerThirdPersonSevarog20261016/FirstPersonReadyV14/`。
- 流程：`prepare_fp_hold_v14.py` → `author_fp_ready.py` → `save_fp_ready_v14.py` → `FirstPersonReadyV14/publish.py`。
- 目标与臂长换算：`ready-reference.json`。
- 实际执行的求解器副本：`solver-generated.py`；原有 V13 作者源不修改。
- 独立包：`/Game/Characters/JasonPlayer20261003/WarhammerSevarog20261016/FirstPersonReadyV14/Animations/`。
- 18 个动画，沿用并替换现有 19 项持握/移动配置。无需 C++ 改动。

实际保存、commandlet 退出及配置发布分别记录在 `assets-saved.json`、`save_fp_ready_v14-commandlet.json`、`assets-published.json`。未主动运行游戏、截图、渲染或测试；观感由用户确认。

19:44 完成实际保存与发布：18 个新动画资产已保存，保存 commandlet 退出码 0，19 项既有引用已从 RelaxedGripV13 切换到 FirstPersonReadyV14。期间等待工程已有 Editor 编译完成后才进入保存批次，未修改其他任务源码或中止进程。本轮没有 C++ 改动。重新进入游玩、新角色组件初始化时加载新配置。

用户随后否定本版的僵硬观感，要求修正人物歪斜后按参考源来。当前已切换到 [V15 原始 Kwang 持握与移动](steel-warhammer-third-person-source-carry-v15-20261017.md)，保留源右臂与全身表演，仅作固定侧偏、头部稳定和左手接触适配。V14 不作为已认可恢复基线。
