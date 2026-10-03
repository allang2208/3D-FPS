# 突变体-3：蓄力双臂展开与手腕准备 V5

2026-10-02，用户指出起跳前蓄力时手部、手臂仍有扭曲，并呈现环绕胸前的感觉。本轮重排蓄力的双臂准备轨迹，保留现有空中方向和 V4 落地动画。

## 动作安排

- 蓄力前段双手分开，放在各自肩线外侧的身前；肘部向外、向下，保留前臂与胸部之间的空间。
- 0.00–0.22 秒随原下蹲收紧蓄势，两手保持分离；0.28–0.54 秒向前上方抬手进入起跳准备。
- 肘位和腕位使用同一个两节手臂解算；上臂带动原肘关节弯曲平面，前臂在该平面内弯曲，避免由前臂额外轴向扭转补偿上臂方向。
- 早期手腕采用绑定中性旋转，随前臂转向。0.20–0.54 秒用单条最短四元数路径准备现有起跳腕姿，取消蓄力时两层独立掌面定向与翻掌的回绕。
- 0.50–0.60 秒接回原起跳臂链，末帧直接复制原 V3 蓄力末帧的上臂、前臂与手腕局部旋转，衔接已认可的空中片段。

准备位置按实际两节手臂总长制定：双手在自身肩部外侧约 22% 臂长、前方约 40–50% 臂长；解算不改变骨长，不引入运行时 IK。

## 正式修改范围

仅更新 `/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_PounceWindup` 的六条旋转轨：左右 `Arm`、`ForeArm`、`Hand`。

蓄力仍为 0.60 秒、60 fps、0–36 帧。肩锁骨、躯干、原下蹲与脚部、指型、全部位移／缩放以及空中、落地正式资产均不写入。本轮没有修改原生 C++、模型、蒙皮、骨架、飞行和伤害时序，无需原生构建。

## 实际制作与保存

目录为 `SourceAssets/Mutant3Khaimera20260923/pounce_open_windup_v5_20261002/`。

- `read_authoring_geometry.py`、`authoring_geometry.json`：读取源动作的肩肘腕坐标，用于确定准备位置和实际臂长。
- `author_open_windup.py`、`Mutant3_Pounce_OpenWindupV5.blend`：可重建脚本与可编辑源，继续保留前轮空中和落地动作。
- `animations/A_Mutant3_PounceWindup.fbx`、`animation_contract.json`：实际导出片段及动作时序／覆盖前散列。
- `install_open_windup.py`、`production_hand_keys.json`、`before_content/`：只复制六条旋转轨、保留正式包原位移与缩放，并保留覆盖前恢复副本。
- `install_state.json`、`install-editor-01.txt`：实际保存回执。

制作源、蓄力 FBX 和正式蓄力动画均已保存。桥回执 `success=True`，完成标记为 `MUTANT3_OPEN_WINDUP_INSTALL_COMPLETE 1 production clip`。保存沿用当前编辑器及桥的批次互斥；取得窗口时编辑器已处于可保存状态，没有开启新编辑器或新试玩。

未进行游戏测试、截图、渲染或视觉验收，蓄力动作的实际观感交由用户测试。本轮尚未获用户认可；Khaimera／Meshy 来源许可和本机二进制素材公开边界沿用已有记录。
