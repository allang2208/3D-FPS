# 集成合同与前置

这是本轮增量的恢复说明。先恢复原生丘陵、夜袭、NPC、家具、怪物与身体系统，再按清单合并；不是可独立编译的新模块。公开材料不能替代本机 Content 和合法供体。

## 新玩家、入场与退出

- 将 FPSBodySpawnResources 加入现有模块；预加载器 header 的 UPROPERTY 数组、已捕获类集合、公开 RetainSpawnAssets 声明和 Deinitialize 清理必须一起合入。角色 BeginPlay 的调用紧跟 InitializeWeaponVisuals，早于 ApplyColdSteelProfile，不改默认属性/装备恢复。
- VoxelBuildPreparation 的声明、两个句柄和请求位来自对应 header 补丁；TryInitializeWorld 在等待丘陵 ready 之前开始请求，EndPlay 取消/释放两个句柄。保留调色板 Surface 与 PreviewMaterial 实际软引用，不回退同步加载以绕过错误。
- FPSGameSceneLifecycle 的 Startup / Shutdown 与 FPSGAME 模块对应调用同时接入。只在 World BeginTearDown 清理该场景已注册的 instanced skin proxies，正常组件释放由引擎继续执行。
- FPSStandaloneRuntime 放回 `Plugins/FPSStandaloneRuntime`；只包含本项目原创描述/源码，PythonScriptPlugin 仍来自本机 UE。其 UncookedOnly / Editor 目标限制不可改成打包 Game 硬依赖。保留 GIsEditor/commandlet 排除及 Python 延迟初始化等待。
- SmithAppearance 使用居民公开的 `AppearancePaths()` / `IsAppearanceCompilationPending()`，路径必须与居民装配相同。当前宿主已将这两个方法转发给 FVillageArtisanAppearance；该并行重构不属于本批，不用本发布材料覆盖它。没有此 helper 的前置可复用原居民的 Body/Head/Outfit/StandingBreath 清单。SmithReadiness 片段是共有准备条件，已有 helper 时不再创建第二份。
- EntryCleanupRequested / EntryCleanupGCTime、准备末尾 GC 请求与实际 GC 时间比较同时合入。不在后加入主机每次创建 Pawn 时重复收集，不在多世界 PIE 中使用此进程级分支。
- 村庄种植快照依赖现有 BeginVegetationCell / CompleteVegetationCell / GetVegetationStrip 合同与全局 CandidateId。保留其他任务已认可的绘制策略，本批只调整生成工作的批次。
- 草地 ArePassShadersReady 声明/实现、DrainPendingStamps 与 RecenterWindow 两个调用都要合入；未就绪保留队列，不能返回后丢弃待执行效果。

## 夜袭资源和持久化

新增 HillsNightAssets、HillsNightPersistence、HillsNightRaidSave、HillsNightReplicationGate 后，原 HillsNightRaidSubsystem 中旧 PrepareAssets / AssetsReady 定义应移除，避免重复定义；保留本机已有的刷怪选址和战斗逻辑。

类声明需要这些接口：OnWorldBeginPlay override；Checkpoint、IsSessionReady、AreAssetsReady、HasAssetPreparationFailed、IsViewerPrepared；私有 RestoreSession、RestoreActors、WorldTearingDown、CreateRaider、PrepareAssets、AssetsReady、ReleaseNetworkLoadingPolicy、UpdateReplicationGates。状态字段与名称以 [NightState.fragment.h](NightState.fragment.h) 为准；它只摘录本批合同，不能覆盖整个 header。

接入已有生命周期的顺序：

1. Initialize 注册 `FWorldDelegates::OnWorldBeginTearDown` 到 WorldTearingDown，沿用原配置读取；客户端也创建子系统和资源请求。
2. OnWorldBeginPlay 在实际 NetDriver 存在后启用该 GuidCache 的异步加载，并开始 PrepareAssets。
3. Tick 先 PrepareAssets，再对 NM_Client 返回；权威端 UpdateReplicationGates、RestoreSession，然后保留已有输入准备门禁、导航和夜袭时钟。只在资源及 RestoreActors 就绪后继续生成。
4. 按现有 NextCheckpoint 周期保存；昼夜/夜次变化、门生成/重选与成功生成怪物时 Checkpoint。GetGroundPins 也包含 PendingSave 中尚未恢复的怪物位置，保证恢复时能等到地面。
5. SpawnOne 复用 CreateRaider，不能重复扣除预算或把保存恢复算作新一波。被保存的 SpawnedThisNight/WaveRemaining 与存活列表有不同含义。
6. WorldTearingDown 在依赖销毁前保存；Deinitialize 恢复网络加载策略、释放复制门禁/句柄并解绑世界回调。

NurseZombie 的 IsNetRelevantFor 声明与 gate 文件中的定义成对；只作用于 HillsNightRaider 标签。Portal 的 AddAssetPaths 方法复用已有 FramePath/CurtainPath/MaterialPath/BeamMeshPath/BeamMaterialPath 常量，并由 BeginPlay 使用。MonsterStunSharedManifest 只替换默认眩晕路径与加载分支，保留原骨架匹配、播放与 RPC；HumanoidKnockdownComponent::DefaultAnimationPaths 前置也必须存在。

Wildlife 的 AmbientAudioLoads 字段、初始化请求、生成前就绪判断和 Deinitialize 清理成套接入；HillsWildlifeAudioManifest 统一 AppendTakes/LoadTakes/AssetPaths，并在 header 声明 `static TArray<FSoftObjectPath> AssetPaths(const FString& Id);`。保留原声音选择与联机事件。

## 家具、制作和复查工具

Configuration 中仅有 ChapelPew 类型、座位与本轮动画绑定，不能覆盖整份 player_body / furniture_rest。相机完整采样保留本机，由已有 `Tools/PlayerBody/config_transaction.py` 按具体字段写入；配置摘录列出必要键与采样散列。已有通用消费者为 `Movement/FPSFurnitureRestComponent.*`、`FPSFurnitureRestCamera.cpp` 和玩家身体动画读取链，保持进入/坐稳/起身及占位权威语义。

制作工具仍需 `SourceAssets/TemperateHillsOldChapel`、`TemperateHillsVillage`、ChapelFurniture R2/R3、铁匠铺 R2/R3/R6/R7/R8 混合输入与合法 Content。早期作者/预览入口保留为配方，不自动重跑旧版本覆盖当前资产。公开工具不等于资产已导入。

联机夹具只在显式参数和私有项目路径下创建。HillsNetLoad 依赖 HillsContinuitySupport；构建/运行/Trace 导出脚本不在此次整理中执行。后续复查使用保留的隔离快照或用户授权的新副本，不能指向正式 Saved/SaveGames。
