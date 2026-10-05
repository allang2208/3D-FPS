# M08 地面／墙面／顶面移动 V02

按用户要求，在已保存的伏窥者上增加爬墙、跳跃越障和跨高度飞扑。参考悬钟 `M09CeilingRoute` 的真实实体支撑、体积净空、逐段带碰撞移动；扩展为任意表面法线，保留 M08 自己的模型、动作与战斗身份。

## 行为

- 追击与归巢由原 Behavior Tree 驱动，M08 的移动分支沿实体表面建局部路线；不再走地面 NavMesh 的 MoveTo。
- 地面、斜坡、墙面和天花板均可作为支撑；身体随表面方向旋转。阴角贴面转接，凸角增加外侧净空过渡点。
- 越障跳跃先寻找实体落点并扫掠完整弧线，随后沿锁定轨迹飞行；独立 `TraverseJump` 动作无伤害窗口。
- 战斗扑击沿用原单一攻击时钟和一次伤害消费，允许从墙面／顶面发起跨高度扑咬。跳跃途中不持续追踪玩家转弯，仍可躲避。
- 失去支撑时下落；控制打断取消越障跳跃；死亡清除爬行/跳跃意图，交接原尸体机制。BT 的 Hold 不会把正常跳跃冻结在半空。
- 竖直爬行按完整三维速度播放现有爬行动作。新增越障动作复用已制作扑跳姿态，单独保存、单独计时，不重复结算攻击。
- F6 的伏窥者生成不再要求地面 NavMesh；保留实体地面、净空、占地和防重叠条件。

## 初始配置与边界

爬墙速度 180 cm/s，地面追击 210 cm/s；单次跳跃搜索距离 7 m、落点上下搜索范围 5 m。连续爬墙没有固定墙高上限，需要实际连续支撑及身体净空。实体墙体仍阻挡角色，不能穿透封闭几何；无法容纳身体的窄缝不构成有效路线。

表面搜索采用有界的局部 A*，单次最多 40 次节点展开、156 个候选节点、8 个前行路点，路线为空时至少间隔 0.7 秒重新规划；近十二个支撑点用于减少来回折返。它是滚动的表面路线搜索，并不保证任意复杂封闭迷宫中的全局可达性。支撑复查间隔 0.15 秒，实际位移始终扫掠；飞行以最多 1/60 秒的时间段推进。

制作没有改动悬钟资产或其行为；狼／感染犬保持原地面行为。共用捕食者执行层仅增加可覆盖的支撑、转向、落点、轨迹和接触接口。

## 文件与执行

源码：`Source/FPSGAME/Monsters/LurkerM08Traversal.cpp`、`LurkerSurfaceRoute.*`、`LurkerM08Monster.*`；共用接入位于 `WolfMonster.*`、`WolfHunting.cpp`、`MonsterBTNodes.cpp`、`MonsterAIController.cpp`、`Development/DevelopmentSpawnComponent.cpp`。

资产保存脚本：`Tools/LurkerM08/install_traversal.py`。本目录 `Before` 保留此次配置前的蓝图和动作集，`installation.json` 记录实际保存状态。

已实际保存的 UE 资产：`/Game/Monsters/LurkerM08/BP_LurkerM08`、`DA_M08_AnimationSet`、`Animations/A_M08_TraverseJump`。越障动作由现有扑跳动作另存，动作集配置为无伤害窗口。

首次后台构建完成了 C++ 源文件编译，但最终 DLL 链接因正在运行的无界面导入进程占用文件而失败；原始记录保留在 `build_attempt01.log`。随后 `Tools/LurkerM08/Build-Traversal.ps1` 等待现有构建／编辑器进程释放后执行补编译，没有停止其他进程。

2026-10-04 已读取补编译完成结果：`FPSGAMEEditor Win64 Development` 返回 `Result: Succeeded`，退出码 `0`，报告 `Target is up to date`、执行 `0` 个构建动作。先前的 DLL 占用阻塞已解除，当前目标无需再次编译或链接。记录见 `build_state.txt`、`build_console.log` 和 `build.log`。这项记录仅说明构建完成，不代表已进行游戏运行或行为测试。

保持原 F6 → 怪物生成 → 伏窥者 M-08 入口。没有主动运行游戏、测试、截图或验收渲染，由用户测试表面切换、落点、扑咬和受击交接。

## 2026-10-05 归档说明

本目录中旧 Before、PreviousSource、before_references.json、Blender 上次保存和已替代定位文件（如存在）已移到 `trash/lurker-m08-retired-20261005/`。按工程 `Docs/Publication/LurkerM08_20261005/archive-manifest.json` 查询原路径及恢复目标；历史段落的旧位置不表示备份仍在本目录。仍供当前制作链读取的正式源继续保留。
