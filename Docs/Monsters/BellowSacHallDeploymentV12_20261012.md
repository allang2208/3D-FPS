# 鼓囊 M-09：两个大厅分层部署 V12（2026-10-12）

用户确认每厅额外加入四只鼓囊，原有每波 12～15 只职员不减量；每厅一楼两只、二楼两只。共八只鼓囊，均为普通品阶，随首波分批生成。

## 数量与遭遇

| 项目 | 每厅规则 |
| --- | --- |
| 首波 | 12～15 只随机接待员／安保员／研究员，加 4 只鼓囊，共 16～19 只 |
| 二波触发 | 首波实际击杀严格超过一半，16／17 只对应击杀 9 只，18／19 只对应击杀 10 只 |
| 二波 | 原有检修门出 12～15 只职员，不再增加鼓囊 |
| 总数 | 每厅 28～34 只，两厅合计 56～68 只，其中鼓囊固定 8 只 |
| 放行 | 两厅所有名额都实际击杀后，主题区域原有三个出口统一解锁 |

`AFacilityHallEncounter` 的名额和角色引用由护士类扩展为 `ACharacter`，职员池仍只有原来三类，鼓囊使用四个独立固定名额。通过既有 `UMonsterCombatComponent::GetVitals` 读取两类怪物的权威生命值，沿用唯一名额标签、击杀奖励、死亡去重及遭遇结束清理。未死亡就被删除的角色仍重试原名额，不作为清厅。

## 楼层落点

- 一楼两只使用现有厅内可走区域随机落点，保持玩家附近 4.5 米避让，同厅鼓囊出生时保持间隔。
- 迎宾大厅二楼：沿作者数据中高 450 cm 的两侧开放回廊，各放一只。采样区不包含中庭空洞、东侧封闭办公室。
- 分流大厅二楼：沿作者数据中高 420 cm 的西侧平台两端，各放一只。采样区避开封闭值班室。
- 上层区域使用模块局部坐标；`FDungeonRunNode` 从已有布局清单读取 `yaw`，与 `origin` 一同转换到装配后的世界位置，跟随地牢旋转和高差。
- 所有名额仍要求相容尺寸 NavMesh、真实可走支撑、胶囊净空和四周支撑；地面高度须在指定楼层上下 40 cm 内。上层失败不会降到一楼补数。
- 出生落点受阻时保留名额重试。轮转名额游标保证被占用的上层区域不会阻塞其他首波或二波名额；每次调度仍最多处理一个名额、最多 12 个首波候选点，保留跨大厅生成预算和渲染注册栅栏。

上层区域尺寸依据现有 `DungeonReceptionHall20261006/author.py` 的回廊、`DungeonFacilityTransit20261007/author.py` 的平台与值班室，包含近期开敞楼梯和上层摆设的避让余量。实际路径、站位与画面留给用户测试。

## 用户要求的慢速游荡接入读取

使用既有编辑器桥只读鼓囊正式蓝图和动作集，无运行游戏。读取脚本为 `Tools/BellowSacLobber/read_hall_wander_v12.py`，输出为 `Saved/BellowSacLobber20261012/hall-wander-v12-inputs.txt`：

- 正式类：`/Game/Monsters/BellowSacLobber/BP_BellowSacLobber`。
- 控制器：`BP_MonsterAIController`；`AutoPossessAI = PlacedInWorldOrSpawned`。
- 移动组件：`UMonsterCharacterMovementComponent`。
- 蓝图行走／追击速度均为 80 cm/s，游荡倍率 0.5，因此无其他减速时为 40 cm/s。
- 动作集：V03 `DA_BellowSacLobber_CombatPressure`，慢走标定 40 cm/s，普通移动标定 80 cm/s。
- 共用控制器游荡半径 800 cm，出生错峰 0.5～3 秒，通常每段移动 2～5 米，到点停留 1.5～4.5 秒。

代码链路为 `MonsterBTNodes` 的持续 Idle 任务 → `MonsterWander` → `MonsterCombatComponent` 的 Wolf 适配 → 鼓囊继承的 `AWolfMonster::SetLocomotion`，速度在 `MonsterCharacterMovementComponent::GetMaxSpeed` 中叠加 50% 倍率。四足动画用实际速度推进步态，并沿用 V11 脚步声。

游荡目的地要求完整可达路径、出生点范围和楼层高度限制；发现目标、受击等待确认、控制、攻击、回巢及死亡按原优先级接管。每 0.2 秒处理游荡进展，全局每帧至多两个新目的地请求，没有新增 AI 管理器或 Tick。本次仅检查已有游荡接入，不重复改写 AI。

## 落盘与构建

新增的蓝图类加入生成器已有的异步准备列表；本体、动作、投射物、软体死亡及 V10/V11 声音复用原蓝图引用。现有 `DefaultGame.ini` 已包含鼓囊打包目录，本次不新增资产、不改地图、不需要额外导入。

修改前副本：`Saved/HallBellow20261012/Before/`。本次代码已包含在同一工作区最终串行构建产物中，复用完成结果，未重复构建：

- `FPSGAMEEditor Win64 Development`：`Result: Succeeded`，200.84 秒，已链接正式 Editor DLL。日志副本 `Saved/HallBellow20261012/build-editor-success.log`，原始构建 `Saved/BlizzardFix20261012/Editor-build-final.log`。
- `FPSGAME Win64 Development`：`Result: Succeeded`，221.48 秒，已生成 Game 可执行文件。日志副本 `Saved/HallBellow20261012/build-game-success.log`，原始构建 `Saved/BlizzardFix20261012/Game-build.log`。

途中共享源码的头文件变更及移动接口错误曾使全工程构建失败，已以后续成功结果为准。已有编辑器在必要原生接入前通过现有互斥桥正常结束 PIE 并关闭，当时没有未保存资产；沿用用户此前允许停止及正常关闭编辑器的授权，没有强制结束编辑器进程。

未主动打开编辑器或游戏，未运行游戏／PIE 测试、自动测试、截图或运行时验收。新配置在重新生成的随机地牢中生效，实际站位、移动和战斗效果由用户测试。

全工程构建前置修复：既有 `FPSDodgeMovement.cpp` 的两个 const 读取函数调用了 UE 5.8 非 const 的 `GetRootMotionSourceByID`，产生 C2662。对照本机引擎实现确认该接口只遍历当前／待添加列表，不修改数据，两个调用加最小 const 适配，保留闪避逻辑和公共函数签名；原文件单独保存在上述 Before 目录。没有修改其他任务的移动／枪匠／技能头文件。
