# 蓝图、流送子关卡与插件联机排查（2026-10-13）

本轮按用户要求在后台读取资产与源码、修复并编译。没有启动交互式编辑器、PIE 或游戏，没有执行运行测试，也没有修改或保存 Content 资产。

## 本轮修复

| 问题 | 原因与修改 |
|---|---|
| 同进程双人 PIE 的草地脚步反馈串世界、串角色 | AutoFootstep 的进程级事件原来只有表面类型和位置。现在携带发出事件的 Actor/Component 上下文，反馈组件同时核对世界和所属角色；远端脚步的音频旁路也传递相同归属。每个角色独立维护冷却和足迹池。 |
| 客机或远端角色漏掉草地脚步反馈 | 原来只在 BeginPlay 的 `IsLocallyControlled()` 为真时订阅，控制权稍后到达时不会补订阅。现在显示世界内的角色均订阅，收到自己的事件后再惰性加载资源；专用服务器仍跳过表现。远端接触沿用已有复制移动产生的本地脚步，不增加逐步 RPC。 |
| 换图/断线后旧脚步异步加载回调仍访问旧对象 | 原回调捕获原始世界上下文指针和效果表元素指针。现在捕获弱上下文、弱世界和效果值副本；对象失效、世界变化或正在退出时不再播放旧效果。 |
| 丘陵流送前沿只保护第一个玩家 | 服务端地面生成范围已经包含所有玩家，但未就绪地面的暂停/恢复只操作 Player 0。现在服务端逐个处理玩家，客机只处理自己的角色，记录每人的等待单元和原移动模式。停止速度后仍等待原前沿单元，避免在当前已加载单元上反复解锁。死亡不恢复移动；失去控制、卸载及角色更换会清理暂停记录。 |

变更文件：

- `Plugins/AutoFootstep/Source/AutoFootstep/{Public/AutoFootstepEffectContext.h,Private/AutoFootstepEffectContext.cpp,Private/AutoFootstepAnimNotify.cpp}`。
- `Source/FPSGAME/Movement/FPSFootstepAudioComponent.cpp`。
- `Source/FPSGAME/WorldGeneration/GrassDeform/GrassFootstepFeedbackComponent.h/.cpp`。
- `Source/FPSGAME/WorldGeneration/TemperateHillsStreaming.cpp`。
- 资产读取工具 `Source/FPSGAME/Multiplayer/MultiplayerAssetInventoryCommandlet.cpp`；Editor 依赖增加 `Projects`，用于枚举实际启用插件。

## 覆盖证据

证据目录：`Saved/MultiplayerStreamingPlugins20261013/`。首次修改前的对应源码保存在 `Before/`，不包含对其他会话修改的回退。

| 范围 | 本轮读取结果 |
|---|---|
| 独立蓝图资产 | 718：项目 443、已启用插件内容 275。读取图节点、执行连接、默认对象引用、变量复制标记和 Actor 默认复制状态。 |
| 地图内嵌关卡蓝图 | 30：项目 21、插件 9；合计读取 748 个蓝图对象。 |
| 地图 | 141 个地图包：项目 124、插件示例 17；累计 15,543 条 Actor 记录。 |
| 主地图及引用层级 | 以 `/Game/GameMaps` 和 `/Game/Clearwater` 的 20 张图为起点，沿 StreamingLevel、LevelInstance/PackedLevelActor 引用得到 45 个地图包。新增覆盖 25 个引用场景包，其中 Normandy 常驻流送层 5 个、打包房屋层 6 个、MilitaryTrench 装配层 14 个。 |
| 实际场景详细项 | 上述 45 个包、6,969 条 Actor 记录；没有发现原生预期复制/移动复制被关闭、原生客户端加载标记被关闭、客户端专属可见子关卡，或开启独立物理模拟却未同步的摆放物件。 |
| 包依赖 | 主地图引用闭包 6,093 个包；另追踪原生源码内直接资产字符串，合计定位 59 个相关蓝图对象。引用分析是静态依据，不是运行可达性的证明。 |
| 插件清单 | 枚举当前实际启用的 296 个插件描述符与模块类型。此数字是插件登记数量，不代表逐行审阅整个引擎的 296 个插件。 |

关键文件：

- `assets.json`：全量蓝图/地图/插件静态内容。
- `references.json`、`reachability.json`：包依赖及旧示例错误的引用归类。
- `active-maps.txt`、`active-graphs.json`：主地图流送/关卡实例闭包与相关蓝图。
- `scene-details.json`：45 个场景的复制、客户端加载、流送标记与物理模拟配置。
- `*-output.txt`、`*-result.json`：后台命令输出及退出码。

## 蓝图与插件结论

- 主地图引用的 Normandy 墙体/道路蓝图主要在构造阶段组装几何；墙体使用 RandomStream。关卡实例与常驻子层引用均可解析，没有找到需要新增 RPC 的实际玩法图链。
- FPS 昼夜蓝图是本地光照表现，已有原生天气复制向它写入时间；不把整个环境蓝图改为复制 Actor。
- ZombieDog 蓝图继续调用原生父类实现。项目门、箱子和怪物的原生复制默认值没有被本轮读取的实例覆盖关闭。
- `ColdSteelNet`：读取连接子系统与 GameMode 的登录、退出、出生路径；核心档案生命周期已由项目 WorldSubsystem 接管。未发现本轮需要额外修改的插件通道。
- `AutoFootstep`：发现并修复本轮事件归属、订阅时序、异步对象生命周期问题。
- `AdaptivePathfindingSystem`：读取 AIController、NavData 路径派发及 Nurse/Wolf 接入；实际查询取 `Query.NavData`，怪物逻辑已有服务器权限分支。插件的静态 `DefaultNavData` 目前只赋值/日志使用，没有把它当成本项目实际路径查询跨世界故障来改。
- `FPSBlast` 是 `Source/ThirdParty/Blast` 的求解适配模块，不是 uplugin；其调用沿用服务端建筑承重路径，客户端建筑 Tick 只更新网格和碎片表现。
- PCG 接入沿用复制种子/编辑状态与本地确定性布景，碰撞生成已有服务器全玩家范围；本轮补的是同一路径上的逐玩家移动保护。
- Vibe3D、FabLauncher、建模/MCP 工具等是 Editor 模块；未把编辑器工具接口改成游戏 RPC。禁用的 VoxelFree 不属于当前联机运行路径。

## 发现但不属于当前联机缺口的旧示例问题

全量读取时，8 个未被上述场景或运行源码引用闭包纳入的旧示例/编辑器工具蓝图报告编译错误：`EUB_SnapToActor`、四个 Paragon 演示 PlayerCharacter、两套 PN 素材的 ThirdPersonCharacter、原版 `BP_Lighting_Manager`。主要是失效的旧引擎函数/引脚。详细包路径在 `reachability.json`。

因此全量资产读取进程退出码为 **1**，虽然内容报告完整落盘，不能称为“全部素材蓝图编译通过”。本轮没有扩展为旧素材演示工程的 API 升级。

首次全量报告的 `load_failures` 还包含 30 个地图条目：原因是地图同样发布内嵌 LevelScript 的 GeneratedClass 标签，被工具误当成独立蓝图；这些地图随后均在地图分支正常读取。这一工具分类问题已修正，`reachability.json` 单独记录此类条目，实际读取失败列表为空。后续 45 个场景的详细读取退出码为 **0**，失败列表为空；包引用元数据读取退出码为 **0**。

唯一带 World Partition 标记的地图是素材预览 `/Game/AsianMale_Jason/maps/L_Overview`，不在上述主地图运行闭包内；本轮登记其包依赖和地图内容，没有运行世界分区单元流送。插件示例和归档图的游戏能力不因此被宣称已经联机可用。

## 构建与交付边界

最终 Win64 Development 构建均为 **Succeeded / exit 0**：FPSGAMEEditor 于 20:46:56 完成，FPSGAME 于 20:47:29 完成。记录为 `editor-build-r3-result.json`、`game-build-r3-result.json` 及对应日志；最后一轮实际编译了更新后的 `TemperateHillsStreaming.cpp`。9 个源码文件的本轮前后差异另存 `changes.patch`。

用户测试重点：同进程双人 PIE 中各自和队友脚步是否在正确位置留下反馈；客机出生/重生后反馈是否可用；丘陵中两人分开跑动、传送进入尚未加载地面时是否正确等待并恢复；组队换图后是否遗留旧脚步表现。以上是交付给用户的建议，不表示本轮已执行。
