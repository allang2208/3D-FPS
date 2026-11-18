# 丘陵入场、GC 与再次加入的资源生命周期

适用于 FPSGAME 已定位的入场/新玩家长帧；本页不自动授权运行性能测试。

- 把网络对象反序列化、角色 BeginPlay、周期 GC、导航任务和渲染等待分别归因。网络同步加载计数为零，只说明该监测路径没有阻塞载包，不能说明整帧没有卡顿。全帧间隔不能与嵌套 CPU scope 相加。
- 角色默认装备可能在恢复档案后失去强引用；首次加入缓存命中不证明 GC 后再次加入仍命中。`FPSBodyAssetPreloader::RetainSpawnAssets` 在默认角色装配后、存档装备替换前保留实际直接资产引用；限制到资产，不能沿角色引用遍历整个世界或常驻全部武器目录。GameInstance 结束释放。
- 未烘焙 Editor-Cmd 的 Python 包装器会参与 GC。只有 Trace 确认且独立游戏不依赖 Python 时，才采用 `FPSStandaloneRuntime` 的独立 Game 分支；等待 Python 延迟初始化完成，再释放解释器。编辑器、PIE、commandlet 保留 Python，打包 Game 不引入编辑器插件依赖。不能将该路径的收益直接宣称为打包版 GC 收益。
- 初次载入后的原生引用遍历仍可能很重。当前丘陵在输入解锁前请求引擎安全帧末 GC，并等实际 GC 时间变化；不在 Actor Tick 内同步 FlushAsyncLoading，不改正常 GC 周期，不对其他 PIE 世界发起进程级收集。这是把必要工作归入加载准备，并不表示 GC 工作量消失。
- 包加载完成早于未烘焙骨架/网格编译完成。复用实际消费者的软引用清单提前准备铁匠、建造预览与动物音效；注册网格或设置 SkeletalMesh 前轮询可用的编译状态。只跳过 NullRHI / DedicatedServer 的纯 GPU 预热，保留玩法资源准备与回调。
- 村庄植被关系计算和实例添加分别分片；保留全局候选 ID、竞争邻域、种子与密度。时间预算是软预算，不能抢占一个尚未返回的引擎操作。导航同时任务数会按代理配置相乘；限制提交批次，不擅自降低瓦片精度或移除代理。
- Canvas 绘制可能同步完成材质编译。压草队列及窗口平移可以等待实际材质资源就绪后执行原绘制；需要用户要求复查时确认绘制确实恢复，不能把永久跳过效果当作性能修复。

项目实现入口：`FPSBodySpawnResources`、`VoxelBuildPreparation`、`TemperateHillsStreamingPreparation`、`VillagePlantingDisplay`、`HillsNavigationSystem`、`HillsWildlifeAudio`、`GrassDeformRendering`。历史数字和未完成项见 `Docs/WorldGeneration/hills-lifecycle-network-20261118.md`；其中导航/音效/压草最后一批没有完成无外部竞争的性能复查，不将其候选收益写成验收结果。
