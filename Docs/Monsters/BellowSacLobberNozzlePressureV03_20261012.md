# 鼓囊投掷者：发射管道蓄压 V03

2026-10-12，按用户要求给蓄压阶段增加管道膨胀、收缩和回弹。基于已保存的 V02 抛射动作复制制作，仅修改管道四段骨骼的动画轨道。

- 根部至喷口依次为 `Bone_031 → Bone_030 → Bone_029 → Bone_028`。先轻微鼓动，再逐段充压，各段最大径向膨胀为 16%、19%、22%、20%。
- 约 1.13 秒开始由根部向喷口泄压，喷口约 1.20 秒开始快速收缩；短暂内收至原半径的约 94.5%～96%，随后轻微回弹，约 1.89 秒前恢复。
- 沿各骨骼的局部 X/Z 方向加径向形变，局部 Y 为管道长度方向。以组件空间目标逐段补偿父骨缩放，避免四段膨胀连乘。
- 复制原动作的身体、背囊、腿和瞄准姿态。继续使用 60 fps、2.2 秒攻击时长、0.85 秒锁点、1.2 秒发射的既有时钟；伤害和投射物沿用 V02。

## 已保存资产

- 动画：`/Game/Monsters/BellowSacLobber/V03/Animations/A_BellowSacLobber_Lob_Pressure`。
- 动作集：`/Game/Monsters/BellowSacLobber/V03/DA_BellowSacLobber_CombatPressure`，从当前 V02 配置复制，仅替换 `AttackLob` 动作。
- 原蓝图 `/Game/Monsters/BellowSacLobber/BP_BellowSacLobber` 已绑定 V03 动作集，仍使用原 F6「鼓囊投掷者」入口。V02 资产保留。
- 制作源、FBX、时序参数：`SourceAssets/BellowSacLobberMeshy20261012/NozzleV03/`。
- 制作与导入脚本：`Tools/BellowSacLobber/author_nozzle_pressure_v03.py`、`import_nozzle_pressure_v03.py`。
- 实际保存记录：`SourceAssets/BellowSacLobberMeshy20261012/Records/ue_nozzle_v03.json`，阶段为 `saved_and_bound`；导入完成日志为 `Saved/BellowSacLobber20261012/import-nozzle-pressure-v03-03.txt`。

通过现有编辑器的批次互斥桥接入，为写入动画结束了当时的 PIE，未关闭或重启编辑器。未运行游戏、自测、截图或预览渲染，实际形变观感由用户测试。
