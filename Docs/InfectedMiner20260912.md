# 感染矿工：真人动捕挥击

> 历史版本：此 CMU 动作随后被用户拒绝，已由 [2026-09-13 原始工具动作重建](InfectedMiner20260913.md) 替代。以下动作引用和验收数据仅描述当时版本。

2026-09-12，UE 5.8.2。用户已认可手部，随后拒绝自编攻击和 KayKit 卡通重劈，选择“写实人形的成熟挥击或动捕”。当前攻击已换成 CMU 真人光学动捕，沿用已认可的模型、蒙皮、抓握与矿镐，接入原村庄生成器。新动作的人工观感仍待用户判断。

## 动作来源与适配

采用 [CMU Graphics Lab 的 02_07 swordplay](https://mocap.cs.cmu.edu/search.php?subjectnumber=2)，原始采样率 120fps；使用 [una-dinosauria/cmu-mocap](https://github.com/una-dinosauria/cmu-mocap) 保存的 Bruce Hahne 2010 BVH 转换。先查看源动作，再重定向到实际矿工模型。

- 取首段完整下挥：排除转换器加入的 T-pose，使用 Blender 一基帧 2–266，对应原捕捉 0–2.2 秒，每 4 帧采样一次；输出 30fps、67 个采样点、66 个间隔。
- 保留片段原有节奏，将右手动作镜像到当前左手握镐。完成骨架参考姿态、关节方向、起始朝向和骨长适配，以及垂直接地平移；没有重新编排攻击 IK 轨迹或替换人体关键姿态。
- 保留源捕捉的骨盆相对位移，由既有角色胶囊负责寻路；不启用引擎 root motion 推进攻击。
- CMU 手指没有实际捕捉数据，忽略这些通道，使用已认可的成组抓握。前臂辅助扭转骨按腕部旋转分配；网格、权重、绑定及手指姿态保持既有版本。
- 原始 BVH SHA-256：`40999e80d85823b2a10f0d1175065d86543d22cd115bad759d3c10ddf712c6de`。本次 GitHub API/提交查询不可用，按下载文件散列固定来源，不虚构提交号。候选的 URL/散列见 `SourceAssets/InfectedMiner20260912/Reference/CMU/sources.json`。

CMU 数据允许研究和商业使用，BVH 转换作者没有增加限制；依据随附 `READMEFIRST.txt`，不将其标成 CC0。鸣谢 CMU Graphics Lab Motion Capture Database（NSF EIA-0196217）及转换作者 Bruce Hahne。该片段原身份是持剑挥击，并非专门录制的负重采矿动作。

## 模型、材质和手部

混元男性矿工外形仅生成一次，缓存任务 `1490283299431399424`。主体经 QuadriFlow 重拓扑和 4K PBR 烘焙，身高约 1.90m，保留帽灯、工装、感染皮肤和工靴。

生成的头、躯干、衣裤及鞋继续使用原外形。前臂到手部采用 Manny 连续蒙皮，接缝位于原卷袖内部，保留成熟权重和绑定；左手使用已认可的 VRE 成组抓握。当前主体 12,237 顶点，每侧前臂与手 8,353 顶点，共 160 骨。主体初始转移的四权重限制不代表成熟手部的权重预算。

矿镐木柄 0.96m，镐头跨度 0.72m，固定在左手。身体使用原 PBR 贴图，工具区分木质和锻铁，手套为粗糙深色，前臂读取已有 `MinerForearmColor` 感染肤色。UE 专用 `SK_InfectedMiner_UE.fbx` 仅移除未使用的白色顶点色层，避免 UE 导入错误颜色；认可的 Blender 几何及原始 FBX 未被替换。

手部基线为 `Review/Hand_UserAccepted_20260912`。这个快照含被拒绝的旧 V03 攻击，只可作为模型/抓握参考，不能整体恢复为当前动画。

## 动作与战斗合同

| 动作 | 时长 | 执行 |
|---|---:|---|
| Idle | 10.2667s | 既有人形基础动作，循环 |
| Walk | 3.2667s | 既有原地移动，按实际移速播放 |
| Attack | 2.2000s | CMU 02_07 首段下挥，镜像重定向，单次 |
| Hit | 0.6000s | 既有人形受击，控制期间保持 |
| Death | 物理 | 当前姿态交给布娃娃，没有独立 Death 动作文件 |

镐头约在 1.50s 进入前下方接触位置，伤害窗口为 1.50–1.75s；攻击距离收为 150cm，促使矿工接近到工具实际挥击范围。动画与伤害共用既有战斗时钟，一次挥击最多命中一次，检查距离、朝向、高差及墙体遮挡，打断或死亡取消尚未发生的伤害。

生命 180、基础伤害 24、感知 1100cm、移速 55cm/s、动作后恢复 1.15s、击杀经验 280；实际扣血经过既有玩家防御接口。`AInfectedMiner` 复用人形战斗基类与共享 Behavior Tree，处理追击、攻击、控制等待、返回、死亡和刷新。未新增专属矿镐音效。

## 当前资源与试玩入口

- 蓝图：`/Game/Monsters/InfectedMiner/BP_InfectedMiner`。
- 已认可的模型、Physics Asset、基础动作和材质：`/Game/Monsters/InfectedMiner/AuthoredChopFinal/`。该目录名来自历史导入，本次只复用其中模型及基础资源。
- 当前攻击：`/Game/Monsters/InfectedMiner/CMU02_07/A_Miner_CMUStrike`。
- 村庄：`/Game/GameMaps/L_Normandy_FPS_Test`，沿用 `InfectedMiner_Village_01`，出生点前方偏左约 8m，最多一只。
- 尸体保留 20s，回收后 90s 刷新；出生碰撞失败时 5s 后重试。

双击 `Tools/InfectedMiner/Open-MinerVillage.cmd` 进入村庄。正在运行的旧游戏或编辑器需重启以加载新资源。`Open-MinerVillage.ps1 -Isolated` 打开独立场景；当前规则由用户自行测试，不默认运行 `-Audit`。

## 本地交付与公开源码

- 可编辑源：`SourceAssets/InfectedMiner20260912/Delivery/InfectedMiner_Editable.blend`。
- 引擎导出：同目录 `SK_InfectedMiner_UE.fbx`、四个 `A_Miner_*.fbx` 及 PBR 贴图。
- 实际导出模型预览：`Previews/InfectedMiner_CMU_Attack.gif` / `.mp4`；通用 `InfectedMiner_Attack` 预览已同步本版。
- 当前合同与散列：`Delivery/attack-authoring.json`、`Delivery/rigging.json`、`delivery_manifest.json`。
- 重建与导入入口：[Tools/InfectedMiner/README.md](../Tools/InfectedMiner/README.md)。

已有 Fab/Epic 素材、基础动画和派生二进制的公开再分发许可未核准，完整可编辑文件和 UE 内容留在本机。公开 Git 包含本任务源码、重定向/导入工具、来源清单及记录；仅凭公开源码无法自动恢复完整模型与地图。

## 已完成的记录

原生构建 `build-cmu-final.log` 成功，CMU 导入报告确认 2.2 秒动画、正确资源引用和 1.50–1.75 秒窗口。此前已完成的手部冻结比对确认网格、权重和绑定一致，67 个采样点的手指局部矩阵最大误差约 `1.2e-7`。FBX 重导入为 160 骨，七个时刻主要关节位置最大差约 `0.0000662cm`，旋转报告差为 0；这属于采样测量，不是人体观感评价。

本次村庄运行已完成 21 项、0 失败，覆盖追击接地、前摇无伤害、接触一次伤害、躲避、遮挡、打断、控制释放、真实枪击、奖励一次、布娃娃、死亡取消伤害、回收及再次刷新。尸体实际蒙皮表面采样 2,049 点，缺失地面 0、低于允许阈值 0，最低离地 0.044cm。详见 [validation.json](InfectedMiner20260912.validation.json)，原始日志为 `Saved/InfectedMiner/cmu-village-pass.log`。

这些检查在读到工程新增“交由用户测试”规则前已执行。此后未追加独立场景测试，旧 KayKit 的独立场景通过记录不算当前 CMU 的结果。用户尚未确认本版动作的人工观感。
