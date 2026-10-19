# 生活区三房遭遇（2026-10-17）

按用户指定的三房编成接入现行 `FacilityHallEncounter` 系统，普通员工从此前保存的男性员工、女性员工A、女性员工B 三种 M-01 等概率独立抽取。固定房间身份决定编成，不使用会随反向拼接改变的图深度。

| 顺序 | 模块 | 普通员工 | 螳螂 M-11 | 伏窥者 M-10 | 盲祷者 M-31 | 总数 |
| --- | --- | --- | --- | --- | --- | --- |
| 第一间：员工宿舍 | StaffDormitory | 6–8 | 0 | 0 | 0 | 6–8 |
| 第二间：更衣淋浴区 | StaffChangingShowers | 10–12 | 2 | 2 | 0 | 14–16 |
| 第三间：休闲厅 | StaffRecreation | 6–8 | 2 | 0 | 1 | 9–11 |

员工保持普通品阶与上一阶段的 270/24、230/20、250/22 生命/攻击；螳螂和伏窥者为精英，盲祷者为领主，使用现有模型、动作与战斗数值。螳螂和盲祷者继承 NurseZombie，已在生活区生成分支中排除普通员工的品阶覆盖。

## 触发、落点与数量

- 沿用主题区流程：有存活玩家完整进入生活区后，区域开始，三个房间的既定槽位进入共享生成队列。不是一次同步创建所有怪物，也没有追加第二波或维修门增援。
- 编成通过 `SpawnComposition + RunSeed + NodeRandomSalt` 生成一次；落点使用独立 `SpawnPlacement` 流。数量边界包含两端，员工每个槽位等概率选三种之一。
- 复用 `AuthoredDungeonGenerator` 的异步类资源准备和渲染准备、`FacilityHallSpawnSubsystem` 的世界级分批生成。预分配仅覆盖三种普通员工，新增的螳螂/盲祷者不进入员工专用预分配路径。
- 宿舍使用六间卧室和中央走廊；更衣淋浴区使用两侧房间和中央通道。两个伏窥者在中央通道的不同侧落地，避开淋浴隔间和长凳间隙。
- 休闲厅盲祷者从高顶主通道落地，保持原生体型、胶囊和导航规格；其他怪物使用主厅、通道及 45 cm 休息平台，不使用狭窄厕所作为生成区。
- 所有位置按模块旋转和平移转换，经过已有地面支撑、导航、胶囊净空与走区约束，额外避让玩家和已生成怪物。伏窥者沿用实际表面支撑路径，不强制要求地面 NavMesh。
- 单次调度只处理一个槽位，最多 12 次落点尝试；失败保留原种类、计数和稳定奖励槽位，轮到其他槽位后再重试。非致死删除不计击杀；真实死亡后不再补刷。

## 通行与任务合同

用户在本次对话明确选择：**击败第三间盲祷者后，开放生活区两端闸门。** 内部房间/连接件相通，外侧队友沿用现有区域闸门的入场规则。残余员工和精英不阻止区域开门，但房间清除仍要求该房所有槽位真实死亡，不把首领击败当作三房全清。

| 项目 | 合同 |
| --- | --- |
| 任务 ID / 实例 | `dungeon.exploration` / 当前 `RunId` |
| 目标 ID | `staff_living.blind_supplicant` |
| 显示 | 击杀生活区首领：盲祷者 M-31；数量 0/1 → 1/1 |
| 权威条件 | 第三间专用 `StaffLivingBossSlot` 成功生成后的真实死亡 |
| 开门/路线推进 | `IsStaffLivingBossDefeated()`；区域目标与既有整条主题路线判断共用此条件 |
| 击杀/删除去重 | `bDefeated` + 现有 `DungeonEnemy.<RunId>.<Node>.<Slot>` 奖励身份 |
| 失败与重试 | 生成失败、未生成、非致死删除均不完成目标；原槽位继续等待生成 |
| 共享 | 服务器判定；任意队员有效击杀推进全队同一目标 |
| 复制 | `FDungeonSharedProgress.bStaffLivingBossDefeated`；沿用 RunId/Revision 的新旧快照规则与迟加入状态 |
| 生命周期 | 同一轮跨房间保留；重新生成/解绑地牢清空；不新增跨关闭游戏的战斗断点恢复 |
| 奖励 | 继续使用既有等级、品阶和稳定槽位结算，无额外区域奖励 |

## 实现与交付

- `Source/FPSGAME/Dungeons/FacilityStaffLivingEncounter.cpp`：六种怪物资源、三房编成、原生落点、首领状态。
- `Source/FPSGAME/Dungeons/DungeonRunStaffLiving.cpp`：三房主题区与两端边界绑定、服务器/客机首领状态读取。
- `FacilityHallEncounter.h/.cpp`：生活区分派、品阶、生成确认、真实死亡通知与员工准备范围。
- `AuthoredDungeonGenerator.cpp`：沿已有异步阶段准备六种怪物与闸门资源。
- `DungeonRunSubsystem.h/.cpp`、`DungeonThemeEncounter.h/.cpp`：生命周期、路线通行与统一任务显示。
- `DungeonSharedProgress.h`、`DungeonRunNetwork.cpp`：本轮全队共享状态。

现有三间正式房间和六种怪物资产直接复用，无需导入或重存地图。下一次生成地牢时使用新逻辑，旧运行实例不做现场改造。本轮修改前的相关源码保留在 `SourceAssets/StaffLivingEncounter20261017/Before/`，包含当时已有的并行修改。

构建入口 `Tools/StaffLivingEncounter/build_native.ps1`，结果记录到本轮 `build-FPSGAMEEditor.json` / `build-FPSGAME.json`。按用户规则未运行自动测试、游戏、PIE、截图或验收，由用户测试数量、落点、战斗、开门和联机表现。

### 本轮结果

`FPSGAMEEditor` 与 `FPSGAME` 两个常规构建均成功（退出码 0），正式二进制已落盘。该阶段没有修改 UE 资产包，没有启动编辑器、游戏或测试。数量、实际落点、怪物行为、闸门和主客机表现由用户测试。
