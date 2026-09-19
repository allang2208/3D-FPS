# 四足怪物动作模板：狼母版 V1

2026-09-14 用户指定先建立 UE 中可复用的四足基础动画模板，以狼为首个母版。模板已经制作；用户尚未进行动作/游戏验收，不称为已认可四足成品。默认不测试规则继续适用。

## 入口

- 工程说明：`D:/FPS3D/FPSGAME/Docs/Monsters/QuadrupedAnimationTemplates.md`。
- 原包：`/Game/AnimalVarietyPack`，来源为 [PROTOFACTOR ANIMAL VARIETY PACK](https://www.fab.com/listings/2dd7964c-a601-4264-a53d-465dcae1644c)。本机六个模型：Crow、Fox、Wolf、Pig、DeerStag、DeerDoe。来源页列出的统计与本机原地/RM 文件数量分开记录。
- UE 入口：`/Game/Monsters/QuadrupedTemplates/WolfV1/BP_QP_Wolf_Template`、`DA_QP_Wolf_AnimationSet`、`Rig/IK_QP_Wolf_Source`。
- 作者工具：`Tools/QuadrupedTemplates/read_source_catalog.py`、`create_wolf_template.py`；数据和制作记录：`SourceAssets/QuadrupedTemplates/source_catalog.json`、`template_manifest.json`。
- 原生接口：`Source/FPSGAME/Monsters/QuadrupedAnimationTemplate.h/.cpp`。这是原生姿态图和动画模板 Actor，没有另建空 AnimBlueprint 冒充可播放模板。

## 复用约定

基于狼的换皮、伤口与局部缺耳改造见 [僵尸犬派生流程](wolf-reskin.md)，使用独立角色入口并保留狼动作及战斗合同。

1. 通用的是动作 ID、数据集、时钟与语义骨链；每个目标模型仍须采用自己的目标 Skeleton、IK Rig、重定向与体型修正结果。不能将狼狐骨数相同当成直接兼容，也不套用人形自动骨链。
2. 犬形先参考 Wolf/Fox，粗壮体型参考 Pig，蹄类参考 Deer。借用基础移动不替代怪物身份：扑击、喷吐、角击、尾击等招牌动作按角色制作。
3. V1 提供 21 个动作槽：Idle、IdleAlert、LookAround、Walk、WalkTurnLeft/Right、Run、RunTurnLeft/Right、AttackBite、AttackRunBite、AttackPounce、HitFront/Left/Right、Howl、RestEnter/Loop/Exit、SleepLoop、Death。源不存在的后退、侧移、原地转身、起跑/急停及独立落地不伪造为现成动作。
4. 原始关键帧和时长保留；模板副本关闭 Root Motion、锁第一帧容器根，运行求值不发送源包 Notify。源 `_RM` 变体单独记录；本次本机 `_RM` 动画的 enable_root_motion 也为 false，文件后缀不等于设置已启用。
5. 本机狼有 34 骨，根层级是 `root -> Wolf_ -> Wolf_-Pelvis`；前肢有 Clavicle/UpperArm/Forearm/Hand/Finger0，后肢有 Thigh/Calf/HorseLink/Foot。保留承重骨与容器根的区别，后跗额外骨不按人腿省略。`Wolf_-Ponytail1` 在源父链中位于 Head 下，仅保留为 HeadAccessory；未观看解剖作用前不假设为下颌。
6. `PlayTemplateAction` / `SetActionTime` / `ResumeLocomotion` 为动画接口；真正攻击使用现有战斗时钟驱动源秒数。动画不造成伤害。动作终止和死亡取消后续伤害由现有战斗系统负责；Death 动画不能自动恢复移动，不代表已有布娃娃交接。
7. 源接触帧、伤害窗口、足底同步相位没有凭名称猜测。接触字段为 -1，走/跑 140/450 cm/s 为初始可调设计值，非实测源速度。制作新动作或体型适配前实际查看原动画/视频，记录四足支撑顺序、重心、腾空与接触；按用户要求再预览/测试。
8. 新角色接入时保留源动作、重定向原始结果与修正成品三层。目标动作填同一数据集 ID；长躯干/短腿/重躯干各自调整参考姿态、步幅、肩胛、跗关节、腹部高度、尾巴和攻击器官轨迹。源 IK Rig 只有骨链，不宣称已实现地形足 IK。
9. `create_wolf_template.py` 只创建缺失资源，保留已调好的模板。迭代采用新版本目录；本机原资产、模型、贴图与二进制模板不因公开源码发布而自动获得再分发许可。个人技能与工程镜像同步本参考，默认不追加验收。

## 当前交付边界

### 2026-09-15 普通咬击 V2：用户选择的调整方向

用户同意在当前 Bite 上吸收旧 Godot Quaternius Attack 的重心前送、肩颈和前肢承重配合。制作新动作 `WolfV2/Animations/A_QP_Wolf_Bite_WeightShift`，原 WolfV1 源片段保留；替换狼母版和正式狼的 `AttackBite.sequence`。这次属于新片段的骨骼关键帧修正，不能沿用奔跑 V2 的“没有修改关键帧”描述。

躯干先轻微后收再前送，前移峰值为源姿态之外 8 cm，左前爪轻抬前落，其余足端用源位置约束；前肢两段 IK，后肢保留 HorseLink 的三段 FABRIK，离线写成关键帧并保持脚掌朝向。容器 root、网格、蒙皮及 Actor 位移不改。源时长 20/30 s、额外起势 0.12 s、源接触 [0.2, 11/30) s、伤害和打断合同保留，不采用旧 Godot 提前截断的播放逻辑。

工具 `Tools/WolfMonster/author_bite_v2.py`，参数／本地关键帧／FBX 位于 `SourceAssets/WolfMonster/BiteV2`；详见 `Docs/Monsters/WolfBiteV2.md`。这只是普通咬击修正版，不冒充整套新角色。用户未要求修改后预览或测试，本阶段由用户试玩，离线足端约束不等于实际接地已经验收。

### 2026-09-15 奔跑 V2：旧 Godot 狼参考

用户反馈狼奔跑僵硬，已阅读实际旧工程 `E:/3d/trash/repository-ue5-root-20260910/scripts/main.gd`、`wolf_anim.gd` 及 Gallop 连续帧。实际运行源是 Quaternius 的 0.5667 s 完整 Gallop、固定 1 倍速，模型额外 bob=0；备用 `wolf_rig.gd` 的对角正弦步态不是现役源。`enemy.gd` 的 `_rig_t` 未被这个关键帧驱动器使用，不把注释中的速度缩放写成其实际机制。

UE 共用姿态图在 V2 将走跑切换区间与源速度参考分开；狼追击速度下保持完整 Run，不长期混入 Walk 稀释收腿、腾空和躯干起伏。相位由实际速度除以每周期步幅推进，过渡时混合步幅而不是两个步频。已有左右转向片段按平滑转向速度混合，方向共用归一化周期，缺失槽回退到直行动作。默认转换比率 0.35/0.65、完整转向 120°/s，均在动画数据集 Locomotion 配置。

源关键帧和骨骼保留，未另叠通用正弦摇头、扭腰或整体跳动。角色攻击、移动数值、AI 和 F6 入口保留。说明 `Docs/Monsters/QuadrupedLocomotionV2.md`，配置工具 `Tools/WolfMonster/configure_locomotion_v2.py`。查看源参考不等于修改后通过验收；本次未进行游戏测试或修改后渲染，由用户试玩。

### 2026-09-15 狼角色接入

用户进一步要求完成狼数值、动作状态机、AI 与 F6 自行生成。制作入口为 `/Game/Monsters/Wolf/BP_WolfMonster`，父类 `AWolfMonster`；配置 `/Game/Monsters/Wolf/DA_Wolf_AnimationSet` 复用母版 21 槽，在狼角色副本中填写 Bite/Pounce 源接触窗口及源 RM 根位移测得的步频参考。骨骼关键帧不重新制作。

沿用共用怪物 Behavior Tree、Combat 执行门、血条、防御、流血、弹反与经验；狼自己执行嚎叫召集、咬击、扫掠扑咬、三向受击和死亡转布娃娃。F6 目录 ID `Wolf`，显示“野狼”。数值、时间合同和制作工具见 `D:/FPS3D/FPSGAME/Docs/Monsters/WolfMonster.md`、`Tools/WolfMonster/install_wolf.py`。本阶段未运行游戏、测试或渲染；由用户测试。以下段落记载母版本身的交付范围，不再代表狼角色尚未接入。

已制作动作副本、数据集、狼源 IK Rig、可放置模板蓝图和原生动画入口；必要 Editor 构建及资源生成已完成。没有运行游戏或渲染；没有新目标网格、目标重定向、村庄生成、四足战斗、地形足 IK、音效编排或布娃娃验收。由用户测试后决定具体怪物接入。
