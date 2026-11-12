# 螳螂 M27 左攻击精修 V2

2026-11-08。用户反馈 Beast06V1 攻击僵硬，随后确认继续按建议制作左攻击样板。本轮仅制作左攻击并更新已有对比蓝图；右攻击、受击、待机及飞扑保持其当前引用。

后续接入：用户继续要求自行检查后，[左右普攻 V2 已接入正式 F6 螳螂](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27Beast06V2Pair20261108.md)。以下内容保留左攻击样板阶段记录；当前引用状态以左右接入文档和 `activation_receipt.json` 为准。

## 本轮制作

从保存的 UE 原生 Beast06 Attack1 重定向数据重新开始，使用 ClawV14 第一帧作为准备姿势。没有把 Beast06V1 的失败适配动作继续叠加为母版，也没有重新修改模型、蒙皮、骨长或 UV。

- **换重与足部支撑**：以后脚脚掌前部为转动支点，制作抬跟和转掌，前脚在切入时承重；髋部加入先向后侧、再向主攻侧转移的过程。足部支点来自实际足部网格，腿部按原骨长求解。
- **完整身体发力**：骨盆、脊柱、肩带和臂链读取同一条源动作时间映射。肩、肘、腕没有分别抽取不同源时刻。骨盆先完成收势，胸部稍后，手臂最后回防。
- **刀刃弧线**：从真实刃面和曲刃方向构建带符号坐标，制作斜切、随势切出、弧线回收；目标方向随胸部转动，取消 V1 每帧回拉到旧 V14 世界方向的方式。
- **双刃避让**：允许主刃进入身体前方，副刃向外后侧回收；分隔方向随动作连续变化，整条手臂绕肩修正，保留肘腕关系。修正四元数在同一半球做时间平滑，再施加几何限制。

动作仍为 **0.65 秒、60 fps、40 个采样键**；接触窗 **0.25–0.30 秒**，现有额外恢复时间 **0.10 秒**。后脚抬跟峰值 19°、转掌峰值 11°，是本版制作参数，不是用户已认可的标准值。刃面离地与分隔参数同样是制作约束，不代表游戏内无穿模的验收结论。

## 实际落盘与入口

新动画：`/Game/Monsters/MantisM27/Beast06V2/Animations/A_M27_LeftSlash_Beast06V2`。

已有对比蓝图 `/Game/Monsters/MantisM27/Beast06V1/BP_MantisM27_Beast06ReviewV1` 的 `attack_clip`、`left_slash_clip` 已改为 V2，并编译、保存。蓝图名称仍保留 ReviewV1，表示最初创建的对比角色；它现在混合使用左攻击 V2 与其他 V1 候选。

正式 F6 螳螂 `/Game/Monsters/MantisM27/BP_MantisM27` 本轮未替换。右攻击仍为 Beast06V1；飞扑仍为 PounceV11。本轮没有 C++ 修改或原生构建。

| 交付 | 位置 |
|---|---|
| Blender 与 FBX 制作源 | [Delivery](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V2/Delivery) |
| 制作参数及来源 | [motion_manifest.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V2/Delivery/motion_manifest.json) |
| 实际导入与蓝图保存记录 | [ue_receipt.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V2/ue_receipt.json) |
| 制作脚本 | [author_left.py](D:/FPS3D/FPSGAME/Tools/MantisM27/Beast06V2/author_left.py) |
| 导入脚本 | [import_left.py](D:/FPS3D/FPSGAME/Tools/MantisM27/Beast06V2/import_left.py) |

后台 Blender 导出与 UE commandlet 导入均已结束；动画及对比蓝图保存成功，commandlet 退出码 0。没有启动 UE 交互编辑器、PIE 或游戏，没有新增渲染、离线验收或回归。是否改善僵硬感以及实战中的接触、穿模与地形表现，由用户测试确认；V1 的旧 GIF 不能代表 V2。

原升级计划与飞扑诊断继续见 [Beast06 升级计划](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27Beast06Upgrade20261108.md)。
