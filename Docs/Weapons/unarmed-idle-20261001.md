# 空手双拳待机 · 2026-10-01

用户要求空手时双手握拳，在屏幕下方随呼吸轻微运动。本版使用当前认可的 V7 裸手及 M4 原生绑定，制作完整双臂的下方待机姿态与连续呼吸循环；角色构造注册 `UFPSUnarmedIdleComponent`，运行直接读取作者局部姿态表。

## 手型与摆放

左拳复用 `SourceAssets/StaffQuickCombat20261001/FixV2/fist-profile-v2.json` 的闭拳与拇指修订。右拳通过原生手掌的前向、桡侧和手背语义框架共轭迁移指骨形变，保留右手自身指节长度与绑定；不复制左手 Euler、不对骨骼或网格应用负缩放。

相机坐标为厘米，`+X` 向前、`+Y` 向屏幕右侧、`+Z` 向上。设计腕点为左 `(34,-15,-18)`、右 `(35,16,-19)`，双拳留在画面下方左右，中央保留视野。肩点为左 `(-7,-21,-26)`、右 `(-7,21,-26)`，肩根位于眼后。实际手掌方向由支撑前臂与原生腕关系生成，不为凑单独的掌向而侧折手腕。

肩—肘—腕用原生两段骨长解算；上臂框架来自本 rig 的 rest 弯曲平面，肘按固定铰链屈伸，前臂 roll 从掌宽投影取得。四根上、下臂 twist 辅助骨均保留完整 rest-local 关系随所属骨段运动；原生手腕局部变换、蒙皮及比例不改。完整肩肘数据保存于 `full-pose.json` 的 `anatomy_contract`。

## 呼吸与动作层

循环长 `4.2` 秒，两完整局部端点为 `Exhale`、`Inhale`，权重为 `0.5-0.5*cos(2*pi*t/4.2)`。吸气端点对每侧完整手臂施加绕肩的小幅俯仰 `-0.18°`，并前移 `0.18 cm`、上移 `0.14 cm`。运行以同一权重混合局部位置和最短路径归一化四元数，再计算整链 FK；不逐帧随机抖动手腕或手指。

出现时用 `0.18` 秒 SmoothStep，从待机姿态下方 `6 cm`、后方 `2 cm` 进入。呼吸相位连续累计；离开空手状态后停止可见视模刷新。

`UFPSUnarmedArmsMeshComponent` 继承现有 `UFPSCastingMeshComponent`，先生成双拳呼吸基础，再执行已有左手施法与药水动作层。右拳保持待机，衣袖、手套继续跟随同一视模 leader；不新增攻击动作、伤害判定或空手近战权限。

## 显示与资源接入

装备状态在 `UColdSteelStatusModel::OnChanged` 发布时读取一次 Snapshot 并缓存。当前主副槽按活跃组 `6/8` 或 `9/11` 取值，两槽全空且没有 `ActiveProductionTool` 时才具备显示条件；每帧不复制角色 Profile。

视模仅在本地第一人称、视图目标为本角色、角色存活且未攀爬时显示。通过软引用异步加载现有 `/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7`，沿用已注册的 M4 服饰 profile；运行隐藏原生 M4 枪体材质区，仅显示手臂。没有碰撞、投影或场景阴影。

## 可编辑源与交付边界

- 作者目录：`SourceAssets/UnarmedIdle20261001/`。
- 作者脚本：`author_idle.py`，保存完整双臂局部表 `full-pose.json` 并生成 `Source/FPSGAME/Weapons/Unarmed/UnarmedAuthoredIdle20261001.h`。
- 可编辑源：`Unarmed_V7_ClosedFistIdle_20261001.blend`，take `A_Unarmed_V7_ClosedFistIdle_Breath_20261001`，`120 Hz`、含循环末端共 `505` 帧；保存记录为 `editable-source.json`。
- 运行接入：`Source/FPSGAME/Weapons/Unarmed/FPSUnarmedIdleComponent.h/.cpp` 与角色构造的 `UnarmedIdle` 注册。

运行直接使用 C++ 完整局部姿态表，不需要另导入 UE AnimSequence。实际构建、产物落盘与生效范围以 `SourceAssets/UnarmedIdle20261001/integration-completion.json` 为准；可编辑源保存不等于构建完成或视觉验收。

当前 `FPSGAME` 的 Win64 Development 后台构建返回成功。主工程编辑器处于打开状态，`FPSGAMEEditor` 构建暂缓，保留其已加载模块；保存并退出主工程编辑器后，执行作者目录的 `build.ps1` 完成 Editor 模块构建，再由用户自行打开游戏查看。没有主动退出、启动或重启编辑器。

构建中同时修正新组件对相机的 protected 成员访问，并将现有 `HundredEyedSlagMonster::EnterCorpse` 的局部 `Mesh` 变量改名为 `CorpseMesh`，消除 C4458；未改变该函数行为，改名前源码保存在作者目录 `BeforeCompileFix`。

本次未启动 UE、运行游戏、渲染、测试或验收。上述位置与运动幅度是本版设计参数，实际屏幕构图、握拳观感与既有动作的衔接交由用户在游戏中测试。
