# 高地双手剑：横扫、棱脊突刺与风誓配重

本批保存高地双手剑的阔锋横扫、棱脊强化突刺、剑尖汇聚特效、刃根与护手适配、风誓轻量配重，以及这一轮发现的联机计时修复。名称统一为“高地双手剑”。

## 当前行为

- 阔锋重刃为传说改造。重击韧性伤害 ×1.5，重击后 4 秒内左键可接一次前方 180° 横扫；半径为普通斩击的 125%，物理伤害为首段普通攻击的 160%。横扫采用 2 倍播放速度，确认命中停顿 0.06 秒；无韧性或破韧目标由服务器统一击飞，本击破韧也可触发。
- 棱脊穿甲刃为传说改造，基础攻击距离 +25%。普通第三段和冲刺攻击直接替换为矩形突刺，每个目标每招只结算一次；在原招式伤害上乘 1.5，另加 20 个百分点物理穿透、招式判定距离再乘 1.25。第三段保留原有 1.4 倍加成为 2.1 倍。重击沿用原重击伤害，另加 80 个百分点穿透和 25% 招式距离；均叠加原刃身 10% 穿透并受统一上限限制。
- 突刺伸出段加速，最远姿态固定停留 0.3 秒，再恢复；普通第三段的动作倍率为 0.8。蓄力抖动幅度和频率各降低 30%。剑气为 25–30 条半透明线，随机分布在镜头周围；当前剑尖与发射空间随玩家移动更新，余辉为 0.55 秒。
- 风誓轻量配重为特殊改造：持用该剑时奔跑体力消耗 ×0.85，重击蓄力速度加成 +0.20。使用统一加法加成公式，不将已经缩短的蓄力时间再次直接除以 1.2。
- 重击起手、连段与突刺接触使用受限同步时间，修复包延迟变化导致的蓄力不足和合法连段被拒；服务器保留实例、序列、目标去重、范围及资源检查。

## 源码、配置与恢复

[源文件清单](source-manifest.json)区分正式文本与精确暂存投影；[共享宿主清单](shared-hosts.json)列出本批接入补丁和 UTF-8/LF 散列。完整本机宿主含其他任务尚未发布的改动，本批没有把这些改动整文件提交。

共享宿主补丁位于 `Integration`，仅保存本批差量。`before_sha256` 是当前完整宿主扣除本批差量后的文本散列；`after_sha256` 是本轮宿主散列。匹配 before 时，从工程根执行 `git apply --check --unidiff-zero <patch>`，再应用；匹配 after 时已经接入。其他散列须按实际宿主合并，不能直接覆盖。公开检出不包含全部宿主前置改动，未对公开切片单独进行 UE 构建。

配置包含 `highland-claymore-modules.json` 的当前刃身、五种匹配护手、两种握柄手指适配和风誓配重；`melee-gunsmith.json` 只提交两种刃身和风誓条目。Jason、Kaitlin 的世界身体横扫键和值列于 [body-roles.json](body-roles.json)，对应消费者补丁也在本批中。第一人称动作由专用执行器按标准柄／长柄文件夹加载。

本机资产入口：

- 棱脊母版：`SourceAssets/HighlandClaymoreMeshy20260922/WedgeSpineJunctionR4_20261106`。正式包仍使用 `/Game/Weapons/HighlandClaymore20260922/RidgePiercer20260927/SM_Highland_Blade_RidgePiercer_V1` 的稳定名称；名称中的 V1 不代表模型仍是废案。对应五种护手位于 `FittedGuardsR2`，当前护手重导入口是保留下来的 `WedgeSpineSocketR2_20261105/publish_guards.py`。
- 风誓母版：`SourceAssets/HighlandGaleOathPommel20261106/SurfaceR2`；正式包为 `/Game/Weapons/HighlandClaymore20260922/GaleOath20261106/SurfaceR2/Meshes/SM_Highland_Pommel_GaleOath_R2`。接口挂载 Z=-22.7 cm，+Z 朝剑尖。保留可编辑母版、固定三角化游戏母版、FBX/GLB 和 4K BaseColor/OpenGL Normal/ORM。
- 横扫作者入口：`HighlandBroadbladeSweep20261104/author_sweep.py` → `VideoFitV3/author_v3.py`。保留 `grip_poses.json`、标准／长柄最终姿态、`Review/Native`、`Review/ReferenceV2` 与 `Review/VideoFitV3` 活跃采样输入。
- 突刺作者入口：`HighlandRidgeThrust20261105/author.py`。保留两柄 fit JSON、`Review/forearms.txt`、`Review/edge.py` 和 `Saved/RidgeThrustAuthor`；刃根制作宿主 `Saved/RidgeLowSeat` 同样保留。
- 跨批前置：`SwordUppercut20261003/GripRecoveryV15/arm_support.py`、`ThrustElbowRepair20260923/elbow_support.py`、实际骨架与原始装备资料。配方不能替代这些本机输入。
- 正式动作、汇聚材质和横扫折射条带分别在 `/Game/Weapons/HighlandClaymore20260922/RidgeThrust20261105` 与 `BreakSweep20261104`。折射使用现有 `AzureRunesword20260913/WristRiftV3/M_RuneRift`。新图标的作者入口为 `HighlandRidgeIcon20261106` 和风誓 `Integration`。

原始参考视频、商业模型/骨架来源、设计图、密集采样、贴图、图标及 UE 包保留在有权使用的本机资产库，未再分发到 Git。当前 Content 入口联接到 `F:/FPSGAMEData/Content`；本次没有移动任何活动 Content 包。视频拟合不等于持有源动画，也不声称骨骼运动百分百还原。

## 归档与已有证据

[归档汇总](archive-summary.json)记录 8,766 个文件、3,742,138,293 字节及逐文件清单散列。退役的风誓 V1、初版燕尾概念、旧棱脊刃身、被替换横扫输出和两次失败的原生检查均已移到 `trash/HighlandSword20261106`；逐项核对移动后的大小和 SHA-256。恢复时使用本机 `manifest.json`，先比较目标路径，避免覆盖新文件。旧目录名中仍有活跃依赖的内容未按日期批量移走。

`Evidence` 保留上轮完整本机宿主的 38 项原生隔离检查、7 阶段真实本机 UDP 结果：监听主机、客机和重连，每端配置 60 ms 延迟及 3% 丢包，覆盖装备、属性与实际重击输入/RPC。Native 与 UDP 不是同一种证据；这些结果未覆盖双人实打伤害/击飞、专服完整战斗以及渲染的剑气和手腕验收。本次只执行发布检查，没有启动 UE 或重新运行游戏。

复用经验已同步个人 SKILL 与工程镜像：武器突刺时钟和剑气跟随、画外手腕及蓄力衔接、镂空金属与连续刃根、服务器攻击回执。导入回执只对产生它的资产修订有效，重新制作时不得用旧回执跳过新资产保存。
