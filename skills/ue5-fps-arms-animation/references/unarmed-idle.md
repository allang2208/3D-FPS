# 空手双拳待机与呼吸

用于当前 V7 第一人称双手全空待机、拳形迁移、低位摆放与服饰接入。2026-10-01 用户要求双手握拳，在屏幕下方合理位置随呼吸轻微运动；这是候选接入，尚无用户视觉验收。

## 作者方法

使用当前认可的 V7 裸手与已有原生 rig，保留绑定、蒙皮、指节与手臂骨长。左拳复用 `StaffQuickCombat20261001/FixV2` 已修订的闭拳、拇指 profile。握拳 profile 表达掌语义空间中的累积指向，不是可直接复制到另一侧的局部 Euler。

迁移右拳时从实际原生骨架提取掌前向、桡侧、手背框架，令 `T=RightPalmFrame*LeftPalmFrame.T`，将左侧指骨形变以 `T*Deformation*T.T` 共轭到右侧，再乘右侧 rest 旋转。语义框架可能含左右手的反射关系，仅用于旋转共轭；不把反射放入骨骼变换或网格缩放。右手局部位置从右侧原生骨长生成，不搬左手指骨位置。

先安排镜头后的肩与下方腕点，再按原生骨长求肘支撑。肘极由期望前臂/掌向关系生成，肘点在两骨圆上取值；不要只搬手而复制原肘。上臂依据实际 rest 弯曲平面建框架，肘保持铰链屈伸；掌向 roll 通过前臂分配。腕局部变换保留原生关系，避免强行独立掰腕。upper/lower twist 辅助骨保留完整 rest-local，随骨段一致运动。

## 连续低幅呼吸

制作呼气、吸气两个完整局部姿态。呼吸驱动用确定性的余弦周期和同一组局部混合权重：`w=0.5-0.5*cos(2*pi*t/Period)`，位置线性混合，旋转用最短路径归一化四元数混合，然后一次 FK。循环末端回到起点；不用每帧随机噪声分别晃手或手指。

当前版周期 `4.2 s`。吸气对完整手臂绕肩俯仰 `-0.18°`，前移 `0.18 cm`、上移 `0.14 cm`。腕点相机厘米为左 `(34,-15,-18)`、右 `(35,16,-19)`，肩点为左 `(-7,-21,-26)`、右 `(-7,21,-26)`。这些是本版设计参数，不是跨 FOV/分辨率已验收的通用摆位。出现用 `0.18 s` SmoothStep 从下方 `6 cm`、后方 `2 cm` 进入。

可编辑 Blender take 用同一余弦时钟和局部四元数混合，`120 Hz` 稠密保存，一周期含末端共 `505` 帧。作者源保存与游戏构建、视觉观感分别记录。

## 状态与既有动作层

空手视模使用现有 V7 M4 手臂与服饰 profile，隐藏枪体材质区，保留手臂材质区。装备服饰继续使用同一姿态 leader，不能另造一套无服饰注册的手臂复制品。

装备状态在 `Model.OnChanged` 时读一次 Snapshot 缓存：活跃组主副槽 `6/8` 或 `9/11` 全空，且无 `ActiveProductionTool`。可见状态还要求本地、第一人称、视图目标为本角色、存活、未攀爬。显示条件与动作表分离；不在每帧复制完整 Profile。

基础待机由 `UFPSUnarmedArmsMeshComponent` 在现有 `UFPSCastingMeshComponent` 之前生成；已有左手施法、药水动作随后覆盖左侧，右拳与服饰仍跟随基础视模。空手待机只补外观，不能借此增加空手攻击权限或伤害判定。

## 当前文件

- `SourceAssets/UnarmedIdle20261001/author_idle.py`、`full-pose.json`、`save_editable.py`。
- `SourceAssets/UnarmedIdle20261001/Unarmed_V7_ClosedFistIdle_20261001.blend`，take `A_Unarmed_V7_ClosedFistIdle_Breath_20261001`。
- `Source/FPSGAME/Weapons/Unarmed/UnarmedAuthoredIdle20261001.h`。
- `Source/FPSGAME/Weapons/Unarmed/FPSUnarmedIdleComponent.h/.cpp`，角色构造注册 `UnarmedIdle`。
- `Docs/Weapons/unarmed-idle-20261001.md` 与作者目录的 `editable-source.json`、`integration-completion.json`。

运行表是 C++ 完整局部姿态数据，无需导入 AnimSequence。后台制作与必要构建按用户规则进行；本次未启动 UE、运行游戏、测试或渲染，视觉观感由用户确认。后续不能把源数据骨长、构建成功或循环端点一致当作用户认可手型、构图与腕肘观感的证据。

## 同日后续：收回双拳与空手走跑

用户随后要求两套装备栏允许切到空栏、待机手臂收回并按法杖空闲左臂制作右臂镜像。当前运行表更新为 `UnarmedAuthoredLocomotion20261001.h`，旧 Idle 表及制作源保留作历史输入。新作者目录为 `SourceAssets/UnarmedLocomotion20261001/`，实际保存 `Unarmed_V7_Locomotion_20261001.blend`，含 Idle、Walk、Run 三个 120 Hz take。

新待机腕点相机厘米为左 `(29,-15,-18)`、右 `(30,16,-19)`，比上文初版各后收 5 cm。保留原拳形、拇指、肩锚点与 4.2 秒呼吸；按原生两骨长度重新求肘，避免只把手腕拉回。

走跑作者源参考法杖 `LeftGaitV16` 的肩、肘、腕轨迹。右侧按相机反射与原生掌语义框架迁移方向，并重新求解右侧原生肘铰链和骨长；作者表中右臂已偏移 PI，运行时不要再加半周期。每个 Walk/Run 循环为 32 个双臂完整局部采样，指节闭拳和辅助骨 rest-local 保持。

运动相位直接读 `UFPSFootstepAudioComponent::GetStridePhaseRadians()`，与相机和法杖使用同一脚步距离时钟。停启及走跑切换只淡入淡出幅度，不重置相位；空中、滑铲与闪避淡出，蹲伏减幅。运行先混合 Idle/Walk/Run 的肘屈伸和前臂 roll 标量，以 `Q(hinge,flex)*LowerRest*Q(forearmAxis,roll)` 重组下臂，再一次局部 FK。其他骨骼采用局部位置与最短路径四元数混合；原有左手施法/药水与服饰覆盖顺序保留。

空栏选择需要贯穿切换和存档整理：`CycleWeapon()` 直接切换主手槽 6/9，即使目标为空；`RemoveRetiredWeapons()` 仅在实际移除活跃退役武器时回退，不能因为当前空栏就自动选另一栏。仍以主副槽都为空且无生产工具决定空手视模。制作、源码接入、Game/Editor 常规构建及未测状态分别见作者目录 `integration-completion.json` 和 `Docs/Weapons/unarmed-locomotion-20261001.md`；构建完成不等于动作观感已获认可。
