# 螳螂-M27：突变体挥爪适配 V3（2026-10-06）

用户反馈原镰刀攻击太慢、僵硬、缺少打击感，指定参考突变体-3 的挥爪动作。本版采用其现行 KhaimeraV2 的 ClawB 和 ClawA，分别制作左镰上撩、右镰斜劈；已实际导入并保存到原 F6 蓝图，未运行游戏或渲染验收。

## 动作与时序

| 项目 | 前版 | ClawV3 |
| --- | --- | --- |
| 每段动作 | 1.3667 秒 | 0.70 秒，60 fps |
| 命中窗口 | 0.48–0.68 秒 | 0.22–0.33 秒 |
| 动作结束后恢复间隔 | 0.45 秒 | 0.20 秒 |
| 左右挥击 | 手工关键姿势 | ClawB 上撩 / ClawA 斜劈 |

通过 UE 原生 IK Rig / IK Retargeter 迁移完整身体动作，等关节数的四肢采用 OneToOne，脊柱与颈部采用插值映射。离线制作保留转髋、胸部反扭、肩肘配合；按长镰刃调整整条手臂的离地角度，减少非攻击镰臂的反向摆幅。脚部按原 BindingV2 脚底和供体膝面适配，整体时间重排包含准备、快速切入、随势和回收，不改变镰刃的刚性绑定。

继续使用 BindingV2 的模型、权重、Skeleton、物理资产和其他动作。原攻击包留在原路径，未改突变体-3 的源资产。沿用既有镰刃扫掠、单次命中去重和伤害逻辑，蓝图同步调整接触时间；无新增运行时 IK 或原生代码改动。

## 本机制作与保存

- 制作目录：`SourceAssets/MantisM27/ClawV3/`。
- 可编辑源：`Delivery/MantisM27_ClawV3.blend`；两段 FBX 与 `motion_manifest.json` 同目录。
- 正式动画：`/Game/Monsters/MantisM27/ClawV3/Animations/A_M27_LeftSlash_ClawV3`、`A_M27_RightSlash_ClawV3`。
- 正式入口：`/Game/Monsters/MantisM27/BP_MantisM27`，F6 名称仍为“螳螂-M27”。
- 保存回执：`SourceAssets/MantisM27/ClawV3/ue_claw_receipt.json`，记录原引用与新时序。
- 重建顺序：`Tools/MantisM27/read_claw_sources_v3.py` → `retarget_claws_v3.py` → Blender 执行 `author_claw_v3.py` → `import_claw_v3.py`。最后的导入脚本仅在明确指定 `-M27ConnectClawV3` 时接回正式蓝图；运行中的编辑器通过已有桥调用其 `connect()`。

参考是本机已有 Epic Paragon Khaimera 的派生动画，来源沿用突变体制作记录。原始包、密集姿势、派生 FBX/Blend/uasset 留本机，不按 CC0 公开。原生重定向及资产保存完成不代表游戏打击感、碰撞或视觉效果已获认可，由用户重新生成 M27 体验。
