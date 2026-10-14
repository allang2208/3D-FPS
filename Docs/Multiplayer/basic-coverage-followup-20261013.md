# 联机基本功能继续排查与修复

本批继续检查角色生命周期、消耗品与库存回执、工作站、移动反馈和采集表现。按用户要求后台修改和编译；不启动编辑器、游戏或自动测试。

## 本批修复

| 问题 | 原因与修改 |
| --- | --- |
| 客机旧档案回写血量，以及死亡期间误复活 | 档案上传反复对同一 Pawn 调用 `AttachPawn`，而该函数把零血量当作新角色重生。现在同一 Pawn 不重复执行重生流程；服务器读取实际血量，上传数据不再回血或复活。新装备、属性导致最大生命变化时仍按权威最大值补偿，保留已损失的血量。死亡状态在旧 Pawn 销毁前进入角色档案，新 Pawn 按原规则重置生命、体力、感染和生存资源。客机不再通过档案应用或被动回复改写复制血量。 |
| 客机受击没有本人视角反馈 | 原红色受击渐变作用于服务器上的 PlayerCameraManager。现在通过角色所属客户端 RPC 播放，主机和客机均在自己的视角收到反馈。 |
| 看不到或听不到其他玩家的脚步、涉水反馈 | 脚步组件原本直接跳过非本地角色。现在近处远端玩家使用已复制的移动位置重建脚步、落地、涉水和尾流；远端声音带空间衰减。复用原水面效果预算，不发送逐脚步 RPC，不在专用服务器加载这些表现。 |
| 木工加工结果没有服务器回传 | 原来仅上传切割操作。现在服务器回传实际木板掩码、姿态、撤销状态、计时、阶段与提示，采用压缩分片和带宽限制。操作序号防止旧快照覆盖新输入；已领取成品不被较旧加工快照退回“待领取”。离开工作台或角色无法操作时停止加工并回传原因。客户端仍可预测拖动，同步路径已衔接当前工作区新增的持久化工件、投入材料、领取及废弃返还接口。 |
| 专用服务器采集生长计时停摆 | 共享采集时钟原来只由本地控制器驱动。现在每个服务器世界只由首个有效控制器驱动一次，监听服务器和无本地玩家的专用服务器使用同一路径。 |
| 客机砍树只有树消失，没有倒伏过程 | 倒树 Actor 原来没有复制。现在复制服务器计算的倒伏计划、资源变换、随机种子和开始时间；客户端异步准备现有树木资产并接续当前进度。倒伏开始时移除同一棵站立树，持久化移除记录仍由原采集快照负责。晚进入可见范围时不重播已经发生的落地声音和碎屑。 |

## 主要入口

- 角色与生命：`Multiplayer/ColdSteelPlayerState.cpp`、`UI/ColdSteelProfileRuntime.cpp`、`FPSGAMECharacterProfile.cpp`、`Monsters/FPSCombatHealthComponent.*`。
- 工作站：`Multiplayer/ColdSteelWoodworkingNetwork.cpp`、`ColdSteelStationNetwork.*`、`Building/WoodworkingSystem.*`、`WoodworkingMask.*`。
- 移动表现：`Movement/FPSFootstepAudioComponent.*`。
- 采集：`Multiplayer/ColdSteelWorldNetwork.cpp`、`Production/ProductionFallingTree*`、`ProductionTreeFallPlan.h`。

## 交付状态

- 修改已写入源码；没有重制内容资产。
- `FPSGAMEEditor Win64 Development` 后台构建成功，项目与 ColdSteelNet 插件 DLL 已更新。最终日志：`Saved/MultiplayerBasicCoverage20261013/editor-build-r3.log`，`Result: Succeeded`，92.67 秒。
- `FPSGAME Win64 Development` 后台构建成功，`Binaries/Win64/FPSGAME.exe` 已更新。日志：`Saved/MultiplayerBasicCoverage20261013/game-build-r3.log`，`Result: Succeeded`，168.19 秒。
- 未运行 PIE、联机测试或性能采样，运行结果由用户测试。
- 本批文件备份与构建日志：`Saved/MultiplayerBasicCoverage20261013/`。备份用于定位修改，不应整体覆盖工作区后续改动。
