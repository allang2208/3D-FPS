# 温带丘陵：进入后长停顿与加载页接入

2026-09-13，UE 5.8.2。按用户要求读取已有游玩日志、修改实现并执行必要原生构建；不启动游戏，不执行回归、性能采样或视觉验收。

## 已有日志中的原因

`Saved/Logs/FPSGAME.log`（用户此前游玩）记录：

- 00:48:09 UTC，旧 `HILLS_READY` 在 406 ms 后触发；只完成 9 个出生地形格。
- 00:48:17 开始构建黑杨 A；耗时 145.39 s，其中 Nanite 125.87 s。
- 00:50:44 开始构建黑杨 C；耗时 153.88 s，其中 Nanite 132.98 s。
- 黑杨 D 构建又耗时 91.31 s。记录同时出现“正在等待蒙皮资产就绪”。

所以旧异步读取将重工作推到了玩家已经能操作之后。顶层资源的加载回调完成，也不等于 Nanite Assembly 子资产、材质着色器和显示资源准备完成。

缓存日志还显示路径变化：上一轮作者进程使用 `D:/FPS3D/DerivedDataCache`，此次游玩使用全局注册表中的 `D:/FPS3D/FPSGAME/Content`。这会使文件缓存查找位置不同；仅凭这些日志不能把所有缓存未命中都归因于路径变化。

## 本次行为

1. `UTransitLoadingSubsystem` 由 GameInstance 持有，跨 `OpenLevel` 生命周期管理同一加载过程。PreLoadMap 使用 MoviePlayer＋不可变 Slate 数据显示切图页；目的地使用全屏 Slate 遮罩继续准备，UI 不读取加载线程上的 UObject。
2. `bSurfaceReady` 只允许加载阶段的角色／相机建立，让 PCG 使用真实出生视野；`bReady` 才表示可放行。期间角色移动关闭，Viewport 游戏输入被阻止；取消按钮和 Esc 由 Slate 处理。完成后 0.3 s 淡出并还原光标和输入。错误保留加载页并提供返回入口，不假装加载完成。
3. 草、灌木、岩石、黑杨 A/B/C/D、雾资源仍分组异步读入，全部在加载页阶段完成。未烹饪 Editor/-game 模式还等待资产编译管理器和着色器任务，覆盖 Assembly 子资产。
4. 每帧建立一个显示样本，树使用与 PCG 相同的 InstancedSkinnedMesh，草灌石使用 ISM，覆盖未必出现在出生点的资产变体。样本无碰撞，加载页关闭前逐帧销毁并等待渲染命令交接。
5. 等待四层实际应生成的 PCG 格子。尚未被调度器创建的格子也算未完成，避免“队列暂时为空”误判。初始视野地形圈与近处树干碰撞一起准备。所需 PSO 数量为零后继续；纹理遵守显存预算，最多额外细化 10 s，不要求所有最高 mip 永久驻留。
6. 已选用的这一套植被资源加载句柄保留在 GameInstance；返回门户不再次卸载，退出进程释放。没有把整个 Normandy 或 Megaplants 库常驻，也不保留离开的地形／PCG 实例。
7. 保留地形 64 m 格、160 m 细节圈／384 m 视野圈、2 个数值任务、每帧 1 个提交；PCG 半径仍为树／石／灌／草 180／120／80／45 m。额外将异步读取、流送注册、注销时间目标设为 2／2／1 ms，仅在丘陵地图生效并在离开时恢复。
8. 项目配置启用 PSO 预缓存与 UE 5.8 的 `r.PSOPrecache.ProxyCreationStrategy=1`。Local/InstalledLocal DDC 固定到项目上一级 `DerivedDataCache`；Zen 默认使用本机 `D:/FPS3D/DerivedDataCache/Zen`。使用项目专属 `FPSGAME-LocalDataCachePath` 覆盖名，不再跟随曾指向 Content 的全局编辑器值；不修改注册表或移动、删除已有缓存。迁移机器可设置该环境变量，或使用 `-LocalDataCachePath=...` / `-ZenDataPath=...`。

## game-dev 加载页迁移

来源项目：`E:/无尽轮回/长期备份/2026-7-13-1/game-dev`。

- `src/world/scene-manager.js` 的 `showLoadingScreen/setProgress/hideLoadingScreen`。
- `ui/panel-theme-backpack.css` 的 `.loading-overlay` 系列：背景 cover、暗色遮罩、440 px 中央卡、24 px 内距、标题、14 px 进度轨、百分比和 0.3 s 淡出。
- `data/loading-screen-config.json` 的随机背景和最短展示；本实现至少展示 1 s，进度按照实际阶段计数，不模拟下载字节百分比。
- 选用已有 `main-hub/gaia-fertile-lands-1.png` 与 `2.png`，复制到本机 `Content/UI/TransitLoading`。它们是原项目加载插画，不代表当前丘陵地图的实机截图。字体和中性灰主题沿用当前 UE 的 `ColdSteelUIStyle`。

复建资源：运行 `Tools/WorldGeneration/Copy-TransitLoadingArt.ps1`。PNG 随本机工程保留，未将来源再分发许可不明的二进制加入公开仓库；Build.cs 将本地图片目录作为 UFS 资源纳入以后打包。没有整包迁移旧项目其它场景背景。

## GitHub 与引擎参考

- [truong-bui/AsyncLoadingScreen](https://github.com/truong-bui/AsyncLoadingScreen)：MIT 项目，参考 MoviePlayer/Slate 的地图切换结构和资源生命周期；本项目独立实现，不安装完整插件，也未复制插件源代码或素材。
- [AsyncLoadingScreen 源码](https://github.com/truong-bui/AsyncLoadingScreen/blob/master/Source/AsyncLoadingScreen/Private/AsyncLoadingScreen.cpp)：参考加载结束后继续等待渲染准备的设计。这里进一步等待 PCG 格子和地形碰撞，使用自己的 world-ready 状态。
- [Epic PSO Precaching](https://dev.epicgames.com/documentation/en-us/unreal-engine/pso-precaching-for-unreal-engine)：使用 `FShaderPipelineCache::NumPrecompilesRemaining()` 控制加载完成；具体 API 和已改名的 ProxyCreationStrategy 按本机 5.8 引擎源码接入。

MoviePlayer 用于阻塞式切图阶段；地图载入后的准备页跟随正常游戏线程刷新。冷缓存中单项资源的 PostLoad／渲染数据提交仍可能让加载页短时停住；本次将这类准备移到放行前，不承诺首次总加载时间消失。尚无本次修改后的 FPS 或卡顿改善实测结论。

## 交付

需重启编辑器或重新启动游戏进程才能加载新原生模块与项目配置。使用原有丘陵传送门即可进入新的加载流程。未运行游戏或视觉测试，由用户测试。

Editor 与 Game 的 Development 原生目标均已完成构建；过程日志为 `Saved/TemperateHills-transit-build-editor.log` 与 `Saved/TemperateHills-transit-build-game.log`。本次不需要重建地图或重新导入树木。
