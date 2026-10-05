# 伏窥者 M-08：犬科参考骨架与动作 V03

用户指出 V01 整体绑骨、权重和动作不佳，要求参考犬科并针对异形骨骼优化。本轮从已有背部 V02 的同一网格继续，保留形体、UV、PBR、五指和背拱孔洞；V01 不作为已认可的动作或蒙皮模板。

## 骨架与权重

- 保留原承重骨、头部和口部命中锚点，增加前臂／上臂过渡骨、肘膝支撑骨，以及左右背拱中段和冠部支撑。
- 四肢、手指、口部、躯干和背拱使用显式解剖分区，约束躯干骨对远端四肢的影响。关节附近使用表面边连接的 screened harmonic 平滑；重合 UV 接缝顶点共享权重求解结果。
- 只为求权重合并重合点索引，没有合并、删减或重新排列显示网格。保留原 625,042 顶点、1,250,160 三角形及自定义法线输入；每顶点最多四个权重。
- 肩胛先滑移，再求解上臂和前臂。肘、膝弯曲平面依据自身绑定姿态确定；后肢单独拟合跗关节，不将其当成普通二段人腿。
- 背拱采用同一个连续变形场：前端跟随胸部，后端跟随骨盆，中段平滑过渡。两侧支撑共享同一前后混合规则，背拱不跟随手臂摆动。

## 动作来源与适配

本地源来自 `SourceAssets/InfectedDogMeshy20260924/GodotRunFitV2/Source/wolf_quaternius.gltf`，沿用工程记录的 Quaternius CC0 来源。源文件 SHA-256 与实际提取动作保存在 `canine_source.json`；本轮未公开分发原素材。

参考 Walk、Gallop、Attack、Gallop_Jump、Idle、Idle_2_HeadLow、Idle_HitReact1/2 和 Death 的身体、肩部及足端控制。没有直接复制犬骨局部旋转：按伏窥者自己的骨长、关节平面和低伏姿态重新求解，在源控制平滑之后施加支撑约束，最终以 120 Hz 烘焙。

走跑保留犬科源的左右错相和支撑顺序，并按 100／210 cm/s 制作支撑相脚轨。长前肢、低矮后肢限制步幅与抬足高度，五指在离地阶段屈伸。重头部采用较小跟随幅度，肩胛和躯干先承重；攻击、跳跃和受击增加承重与恢复过程。

| 动作 | 秒 | 处理 |
|---|---:|---|
| Idle / IdleAlert | 3.00 / 1.80 | 犬科低头待机控制适配，保留四足支撑 |
| Walk / Run | 0.90 / 0.60 | 犬科走、疾驰节奏；目标骨长、肩胛和跗关节适配 |
| AttackBite | 0.85 | 前肢错时承重、巨口咬合、连续恢复 |
| AttackPounce | 1.10 | 后肢压缩推进、前肢接地、落地缓冲与扑咬 |
| TraverseJump | 1.10 | 独立越障动作，保留跳跃时钟映射，不咬合、不结算伤害 |
| HitFront / HitLeft / HitRight | 各 0.55 | 身体受击传递与单侧恢复步 |
| Death | 1.40 | 支撑逐步解除、侧倒，沿用原布娃娃交接 |

普通咬击接触仍为 `[0.30, 0.42]` 秒，扑咬仍为 `[0.52, 0.64]` 秒。飞行位移由原角色逻辑负责，姿态只增加压缩、收肢和落地负重；制作时按根骨局部坐标系换算身体位移，避免将上下运动错误写成前后移动。没有修改战斗数值、攻击时钟、爬墙／顶面移动逻辑或 F6 稳定 ID。

## 制作与接入

- 作者脚本：`Tools/LurkerM08/extract_canine_reference_v03.py`、`author_canine_v03.py`。
- 蒙皮源：`M08_CanineRig_Skin_V03.blend`；完整动作源：`M08_CanineRig_Animated_V03.blend`。
- 导出：`SK_LurkerM08_CanineV03.fbx`、`Animations/A_M08_*_CanineV03.fbx`。
- UE 保存脚本：`Tools/LurkerM08/install_canine_v03.py`。
- 新版资源目录：`/Game/Monsters/LurkerM08/CanineV03`，独立 Skeleton 与 PhysicsAsset；复用原 PBR 材质。
- 正式入口仍是 `/Game/Monsters/LurkerM08/BP_LurkerM08` 与 `DA_M08_AnimationSet`。保存齐所有新动作后切换网格和动作引用。
- `Before` 保留切换前蓝图和动作集，`before_references.json` 保留原引用；V01 源文件及 UE 资源保留。
- 全量安装器会在旧基线和表面移动配置后恢复 V03；单独安装移动配置时保留当前骨架上的越障动作。

`installation.json` 已记录 `canine_rig_actions_saved_and_bound`，新版网格、骨架、物理资产、11 段动作和原蓝图／动作集已实际保存。修正根骨位移后的 `import_final.log` 记录 commandlet 成功、0 个错误。本轮只改制作源与资产，没有修改原生 C++，无需追加模块构建。没有打开交互编辑器、运行游戏、测试或生成预览／验收渲染；动作观感、形变和接地由用户自行测试。

## 2026-10-05 归档说明

本目录中旧 Before、PreviousSource、before_references.json、Blender 上次保存和已替代定位文件（如存在）已移到 `trash/lurker-m08-retired-20261005/`。按工程 `Docs/Publication/LurkerM08_20261005/archive-manifest.json` 查询原路径及恢复目标；历史段落的旧位置不表示备份仍在本目录。仍供当前制作链读取的正式源继续保留。
