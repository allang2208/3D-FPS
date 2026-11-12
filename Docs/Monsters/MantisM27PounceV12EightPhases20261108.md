# 螳螂 M27 八阶段飞扑 PounceV12

归档状态（2026-11-12）：飞扑 V12 已回退到 PounceV11。文末的 V12 作者、导出和动画原路径仅作历史记录，退役文件现在按原相对路径保存在本机 `trash/Conversation20261112/`。

**当前状态：用户否定，已回退。** 用户检查后认为本版不如旧飞扑。正式 `BP_MantisM27` 与原 Beast06 对比蓝图的 Windup / Flight / Land 均已恢复 PounceV11 并保存；普攻 Beast06V2 保留。回退只写三个飞扑字段，没有用旧蓝图文件覆盖其他配置，保存记录为 [rollback_to_v11_receipt.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV12/rollback_to_v11_receipt.json)。本版资产与制作源保留为历史记录，不继续叠加修改，也不作为成功模板。后续候选见 [PounceV13](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27PounceV13LocalTiming20261108.md)。以下内容是本版制作及曾接入的历史说明，不代表当前正式引用或用户认可。

2026-11-08。用户要求按先前八阶段方案优化飞扑、接入正式螳螂，并由用户检查。本轮已完成制作、三个动画资产的后台导入、正式 F6 蓝图和已有对比蓝图的引用更新与保存。未运行渲染、离线验收、PIE、游戏或联机测试。

## 八阶段制作

三个片段保留原时长与原状态接口，在片段内部制作以下八段：

| 阶段 | 片段局部时间 | 制作内容 |
|---|---|---|
| 起势与瞄准 | Windup 0.00–0.12 秒 | 从 BindingV2 待机姿势缓慢启动，先建立轻微前倾，再逐渐举臂 |
| 下蹲蓄力 | Windup 0.12–0.42 秒 | 参考 Beast06 JumpStart 的压缩关系，髋膝配合下蹲，脚掌保持支撑 |
| 蹬地离地 | Windup 0.42–0.60 秒 | 双脚以实际脚掌前部为支点抬跟，髋膝伸展；末帧作为飞行首帧的同一份源姿态 |
| 腾空收腿 | Flight 0.00–0.18 秒 | 从离地姿态逐渐收腿，结合 JumpStart 后段与既有螳螂腾空腿型 |
| 空中蓄势 | Flight 0.18–0.34 秒 | 双刃上举，沿用完整臂链，加入 JumpLoop 的腿部姿态变化 |
| 下劈与伸腿 | Flight 0.34–0.65 秒 | 以非线性节奏下劈，保持真实刃面与内弧方向；末段提前伸腿，收敛到触地姿态 |
| 触地缓冲 | Land 0.00–0.16 秒 | 脚跟落下、髋膝压缩，刀刃切出后制动；参考 JumpEnd 的压缩关系 |
| 回弹收势 | Land 0.16–0.80 秒 | 单次小回弹后逐渐衰减，双刃回防，身体回到待机姿势 |

制作源先生成 **124 个采样点的一条连续轨迹**，然后切片：Windup 使用全局索引 0–36，Flight 使用 36–75，Land 使用 75–123。因此两处切段直接复用同一份骨骼源变换；这属于制作方式，不是对引擎运行混合或碰撞结果的验收声明。

各片段时长仍为 **0.60 / 0.65 / 0.80 秒**，60 fps；之后的原有 0.25 秒恢复门控继续由代码负责。位置轨迹采用保形三次曲线，姿态在统一时间轴上采用同半球的连续四元数曲线，不在每个子阶段停住再启动。

## 来源与适配边界

上身与完整臂链来自既有 PounceV6 的 Khaimera／Mutant3 制作链；长刃使用 PounceV11 同类的真实刃面、弦向和曲刃鼓出方向构建带符号的方向约束。腿部参考来自用户已接入的 Beast06 JumpStart、JumpLoop、JumpEnd 原生 UE 重定向结果。没有使用已否定的 PounceV9/V10。

骨架、网格、蒙皮、UV、骨长保持原 BindingV2。足部支点与足底偏移取自实际网格，腿部按原骨长求解；对刀刃的避让修正从肩部作用于完整臂链，保留局部肘腕关系。双刃分隔和离地高度是制作约束，不表示所有地形与身体表面的穿模问题已经验收。

Beast06 跳跃中的整体骨盆升降被剥离，只提取压缩、伸展、收腿和缓冲关系。角色世界位移仍由原 `LaunchCharacter` 弹道负责，没有新增动画根运动。

## 正式接入

正式蓝图仍为 `/Game/Monsters/MantisM27/BP_MantisM27`，F6 稳定 ID 仍为 `MantisM27`。用 F6 重新生成螳螂即可检查新默认引用；此前已经生成的实例不作为新默认值的检查对象。

本轮只更新以下三个字段，正式蓝图与已有 Beast06 对比蓝图均已保存：

| 字段 | 新资产 |
|---|---|
| `pounce_windup_clip` | `/Game/Monsters/MantisM27/PounceV12/Animations/A_M27_PounceWindup_PounceV12` |
| `pounce_flight_clip` | `/Game/Monsters/MantisM27/PounceV12/Animations/A_M27_PounceFlight_PounceV12` |
| `pounce_land_clip` | `/Game/Monsters/MantisM27/PounceV12/Animations/A_M27_PounceLand_PounceV12` |

普通攻击仍为 Beast06V2 左右攻击。原待机、RunV4 移动、受击、死亡、伤害数值、隐身和刷怪配置未随本轮替换。原 PounceV11 资产继续保留，旧引用记录在保存回执中。

本轮没有 C++ 修改，也没有新增八个网络状态。飞行动画仍按原预计飞行时长映射；实际服务端 `Landed` 仍触发同一次落地伤害、声音与效果。提前或延迟触地继续使用既有状态和姿态快照混合机制，未新增动态空中循环或重写弹道时钟。标称动画切段的连续制作不能代替这些情况下的用户游戏检查。

## 交付与实际状态

| 内容 | 路径 |
|---|---|
| Blender 与三个 FBX | [Delivery](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV12/Delivery) |
| 八阶段、来源、采样切片与参数 | [motion_manifest.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV12/Delivery/motion_manifest.json) |
| 动画与正式蓝图保存回执 | [ue_receipt.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV12/ue_receipt.json) |
| 制作脚本 | [author.py](D:/FPS3D/FPSGAME/Tools/MantisM27/PounceV12/author.py) |
| 接入脚本 | [import.py](D:/FPS3D/FPSGAME/Tools/MantisM27/PounceV12/import.py) |

Blender 已导出并保存制作源。后台 UE commandlet 已导入保存三段动画、编译保存两个目标蓝图，退出码 0。以上是制作与落盘结果，未宣称动作观感、切段、穿模、实战接触或联机表现通过检查。本轮没有生成新 GIF；旧 PounceV11 图片不代表 PounceV12。
