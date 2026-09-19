# 四足奔跑表现 V2

2026-09-15 用户反馈当前狼奔跑僵硬，要求参考旧 Godot 狼的经验优化 UE 四足奔跑。本次读取旧项目实际动作入口、时长和连续帧，调整共用四足姿态图。没有重做网格或蒙皮，也没有更换战斗动作。

## 参考依据

旧工程已迁至 `E:/3d/trash/repository-ue5-root-20260910`。`scripts/main.gd:280` 加载 `assets/models/wolf_quaternius.gltf`，赋予 `scripts/wolf_anim.gd`；移动时播放完整 `Gallop`，`speed_scale=1`。`main.gd` 的狼设定为 3.5 m/s、模型缩放 0.3、额外 bob=0，让关键帧负责身体起伏。

同目录的 `wolf_rig.gd` 是备用 18 骨程序化对角步态，当前黑狼没有使用它。`enemy.gd` 虽然计算 `_rig_t`，但实际 `wolf_anim.gd` 的首个参数是未使用的 `_t`，因此不能把其速度缩放公式误写成当前 Quaternius 奔跑的步频机制。

已查看原工程保留的 `tools/ai-gen/black-wolf-fur-v01-20260906/Gallop-frames-0.jpg` 和 `Gallop-frames-1.jpg`。它们是保留原动作的黑毛材质版本：0–0.125 s 前躯下落、后腿开始前收；0.167–0.333 s 后腿收向腹下，前后肢错开、脊背起伏；0.375–0.500 s 后躯蹬伸、身体舒展，进入下一次腾空。头颈和尾巴随躯干先后变化，不是整只模型同相上下移动。

源 glTF 的 Gallop 长 17/30≈0.5667 s、18 个采样键；Walk 长 32/30≈1.0667 s、33 键。参考图以 24 fps 展示，不能把图序号当源 30 fps 帧号。这里只借鉴完整奔跑周期、前后躯错相和保留源姿态的做法，未将另一套 Skeleton 直接套给 UE 狼。

UE 原包 Run 长 16/30≈0.5333 s，本身有收腿、伸展及头躯起伏；左右转向版同周期且有明确弯身姿态。只读源姿态样本见 `SourceAssets/QuadrupedTemplates/LocomotionV2/source_reference.json`。源 Walk/Run/转向关键帧均保留。

## 改动

1. **走跑过渡与源速度分开。** 原图按标称走速到跑速整个区间持续混合，狼以 380 cm/s 追击时约含 18.3% Walk。现在走跑过渡只占标称跑速的 35%–65%，达到上界后使用完整 Run。狼的过渡范围约 155.6–289.0 cm/s，返巢 100 cm/s 使用 Walk，追击 380 cm/s 使用 Run。
2. **按每周期步幅推进相位。** 原来线性混合两个步频，使短步幅 Walk 拉快奔跑。现在计算 `步幅 = 标称速度 × 源周期时长`，过渡时混合步幅，统一以 `实际速度 / 步幅` 推进相位。源运行速度参考仍为走 92.7、跑约 444.5586 cm/s。按 380 cm/s 的稳态公式，原约 2.06 周期/s，调整后约 1.60 周期/s；这是公式推导，不是游戏测量结果。
3. **接入已有转向姿态。** 平滑采集角色每秒转向角，混合 `WalkTurnLeft/Right` 和 `RunTurnLeft/Right`；120°/s 达到完整转向片段权重。直行时回到直行片段。各方向保持同一归一化周期，不因换方向重播腿部动作。缺少转向槽或 Skeleton 不兼容的目标使用自己的直行动作。

没有额外叠加通用正弦摇头、扭腰、骨盆升降；奔跑舒展和收腿来自原包序列。没有调整移动速度、AI 选择、攻击接触窗口、扑咬轨迹、受击、死亡或 F6 的生成方式。

## 复用与调整

共用实现：`Source/FPSGAME/Monsters/QuadrupedAnimationTemplate.h/.cpp`。数据资产的 `Locomotion` 分类新增 `RunBlendStartRatio`、`RunBlendFullRatio`、`FullTurnYawRate`。`WalkSpeed/RunSpeed` 继续表示源步幅的速度参考，不应为了提前进入奔跑而改错这两个数值。

狼母版和正式狼配置分别为 `/Game/Monsters/QuadrupedTemplates/WolfV1/DA_QP_Wolf_AnimationSet`、`/Game/Monsters/Wolf/DA_Wolf_AnimationSet`。F6 中仍选择“野狼”。其它四足动物可复用姿态图，但步幅、走跑转换范围、足相位及转向幅度仍应按各自动作配置，不复制狼 Skeleton。

作者入口：`Tools/WolfMonster/configure_locomotion_v2.py`。只初始化本版参数，保留已带 `Quadruped.LocomotionVersion=2` 的用户调整；不会改写源动作或原有 WalkSpeed/RunSpeed。源资料读取入口为 `read_gait_reference.py`，只读 Godot 与 UE 源动作数据。

本次按用户要求查看了旧源动作资料；修改后的动画、游戏和 F6 行为未进行测试或渲染验收，由用户试玩。必要构建及配置保存结果另记，不据此宣称视觉问题已通过验收。

交付记录：Editor 必要构建完成，日志 `Saved/BuildEditor/build-20260915-084722.log`；两个动作数据集的 V2 参数已保存，制作日志 `Saved/WolfLocomotionV2Configure.log`，制作清单 `SourceAssets/QuadrupedTemplates/LocomotionV2/authoring_manifest.json`。重新打开工程后，从 F6 生成“野狼”即可使用。
