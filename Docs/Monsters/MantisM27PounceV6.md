# 螳螂-M27：飞扑双镰分离 V6

用户反馈 V5 飞扑双镰交叠。本次仅修订蓄力、腾空和落地的双臂姿态，不改飞扑移动、命中时刻、范围、冷却、破影双倍伤害或回血机制。

- 从 V5 实际制作源继续，保留整身动作与原 0.60 / 0.65 / 0.80 秒时长。
- 蓄力逐渐向外展开；空中左镰略高且靠前、右镰略低且靠后；落地沿各自一侧下劈，随原收势回到待机。
- 仅改变左右上臂旋转轨，让肘、前臂与长镰作为原有完整骨链跟随。骨长、局部位移、缩放、屈肘关系、刚性镰刃和 BindingV2 权重保留。
- 离线按原刚性镰刃的真实顶点构造分段包围盒，以身体肩线中点为左右分界，制作时每侧预留 18–28 cm；地面阶段同时考虑刃面离地。该数值是制作约束，不是实机测量结果。
- 修正曲线跨三段平滑，游戏运行不增加 IK 或逐帧避让计算。

制作源：`SourceAssets/MantisM27/PounceV6/Delivery/MantisM27_PounceV6.blend` 及三段 FBX。

重建：`Tools/MantisM27/author_pounce_v6.py` → `Tools/MantisM27/import_pounce_v6.py`。前者读取 V5 Blend 及 BindingV2 权重/拓扑；V5 仍是制作输入，不删除。

导入目录：`/Game/Monsters/MantisM27/PounceV6/Animations`。仅替换原 `BP_MantisM27` 的 `PounceWindupClip`、`PounceFlightClip`、`PounceLandClip`；数值与其他动作不写入。F6 入口不变。

来源沿用现有 Epic Paragon Khaimera / Mutant3 的 UE 许可派生动作，非 CC0。保存状态见 `SourceAssets/MantisM27/PounceV6/ue_pounce_receipt.json`。

2026-10-06 已通过无界面 commandlet 导入并保存三个 V6 动画及原 `BP_MantisM27` 引用，进程正常退出。原 V5 动画包保留作恢复输入；本轮无 C++ 修改，无需重新编译原生模块。

本轮未运行游戏、渲染预览或自动验收，由用户测试姿态和接续效果。
