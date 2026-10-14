# 动态加载与迟到状态补发（2026-10-13）

继续上一轮蓝图、流送与插件排查，重点读取运行数据驱动的资源路径、异步加载退出处理、迟到场景对象的状态应用，以及同进程 PIE 的换图失败回调。按用户要求，后台修改与构建；没有运行游戏、PIE、渲染、联机模拟或回归测试。

## 修复内容

### 1. 非地牢场景的共享外观遗漏中途加入者

此前 `UDungeonRunSubsystem::FillNetworkState/ApplyNetworkState` 都以活跃地牢 Run 为前提。普通场景宝箱依赖即时 Multicast 开盖，中途加入的客机收不到历史通知。

现在共享的开盖、已搜索容器、破碎玻璃和非复制门状态在普通场景也进入世界快照；地牢仍校验 RunId。没有增加奖励结算、修改任务进度或重新生成宝箱物品。

### 2. 状态先到、Actor 或网格后到时不再永久漏应用

此前客户端遍历当前 Actor 应用一次就丢弃快照，服务器又会抑制相同内容的重复发送。Actor 通道、流送层或网格稍后就绪时，没有剩余状态可补。

现在保留尚未应用的条目，以 0.2 秒间隔继续应用；新快照替换旧的待应用内容。已处理条目从客户端待应用对象中移除，不因等待另一个对象而反复写回旧变换、开启动画。采集镜像对每份快照只应用一次，建筑仍沿用原来应用成功后清空的机制。

宝箱开盖函数现在返回是否已接受表现；网格、骨骼资产或开盖动画未就绪时，不提前写入 `DungeonTreasure.Opened`。即时开盖通知之后仍有世界快照补发，不增加逐帧 RPC。

### 3. 补发状态区分子关卡中的同名物件

流送层的场景快照 Actor 键使用“所属关卡包路径 + Actor 名”，剥离 PIE 包前缀。原先只有 Actor 名，不同子关卡可存在同名对象。常驻层由快照外层 Map 字段标识，继续使用短 Actor 名，避免扩大地牢批量消息；即时通知仍沿用原有确定性生成名。

这是会话内世界快照的键值变化，没有修改玩家存档版本或存档槽。主客机须使用相同的更新后程序。

### 4. 地图载入失败不串到另一个 PIE 世界

引擎在 LoadMap 失败时广播 `PostLoadMapWithWorld(nullptr)`；空指针无法按 GameInstance 过滤。原实现会把每一个接收者的加载界面标成失败。

现在每个加载子系统在带 WorldContext 的 PreLoadMap 通知中记录本次全局加载是否属于自己，只处理自己的空世界失败通知。正常成功通知仍使用原有 GameInstance 判断。

客户端跳过单机加载遮罩时，同步释放此前持有的玩家准备状态、资源准备对象和取消回调，避免只拆遮罩却遗留暂停/旧回调。

## 动态资源与异步路径覆盖

- 读取 `Content/ColdSteelData` 下 56 个 JSON，均可解析。
- 1,320 条直接资产引用对应本机现有资产（去重 1,019）；10 条目录引用存在。
- 四个动画前缀按实际调用角色展开；另包含四种倒树、树桩、切口配置和四种矿石/金属锭材质，合计 45 条展开路径均存在。
- 两条不存在的旧地图路径仅位于 `industrial_exploration_v1.json` 的 `content_state` 历史说明字段；本轮源码搜索未发现读取 `art_baseline/generated_map` 的运行入口，未将其改成新的游戏入口。
- 定向追踪了地牢规划线程的 GenerationSerial/CancelAssembly、分批资源取消、角色头部与消耗品请求代号、服装加载的结束标记、武器/工具卸装取消、传送门 EndPlay、河流/流体/破碎特效子系统清理。已有相应机制的路径予以保留。
- 本机路径存在不等于打包后资源已 Cook/Staging 完整；没有执行打包或加载全部素材包，也不据此宣布所有动态路径已无遗漏。

## 文件与证据

运行实现修改：

- `Source/FPSGAME/Dungeons/DungeonRunNetwork.cpp`、`DungeonRunSubsystem.h`。
- `Source/FPSGAME/Multiplayer/ColdSteelWorldNetwork.cpp`、`ColdSteelPlayerState.h`。
- `Source/FPSGAME/Multiplayer/ColdSteelSharedChestVisual.cpp/.h`。
- `Source/FPSGAME/UI/TransitLoadingSubsystem.cpp/.h`。

证据目录 `Saved/MultiplayerDynamicLifecycle20261013/`：`Before/` 保留本轮首次编辑前副本；`data-paths.json` 与 `expanded-paths.json` 保存路径清单；构建输出和结果按 `editor-build-*`、`game-build-*` 保存。

## 构建与用户测试

最终 Win64 Development 两套构建均 **Succeeded / exit 0**：

- `FPSGAMEEditor`：`editor-build-r2-result.json`，22:54:52 完成，70.29 秒。
- `FPSGAME`：`game-build-r2-result.json`，22:58:49 完成，237.31 秒。

第一轮 Game 构建期间新增的 `RangedAttackQuery.cpp` 未进入当时已生成的文件清单，导致链接缺符号；重新生成清单后通过，本轮未改动该战斗查询实现。期间检测到编辑器/Live Coding 占用，用户保存关闭后才继续最终构建；没有自动重开编辑器。

没有执行运行测试。`changes.patch` 为本轮 8 个源码文件的前后差异，`changed-files.txt` 为文件清单。

用户可重点观察：主机先开普通场景宝箱、客机随后加入时的盖子状态；较慢客机加载场景后门、玻璃和容器是否补齐；子关卡同名物件是否正确对应；一侧加入或换图失败是否影响另一侧的加载界面与输入。
