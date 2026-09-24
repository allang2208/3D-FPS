# 河段试做：水面层次与子弹击水

日期：2026-09-23。承接枪口烟雾和火系魔法优化，按用户同意的“一段河道＋子弹击水”范围制作。资产已保存，C++ 接入源码已完成，必要原生构建命令成功返回。

后续：用户已确认对象引用修复后水花正常显示；当前资产已进行[涟漪与击水细化](river-ripple-splash-polish-20260924.md)，下文保留首版制作与修复记录。

## 范围和表现

丘陵世界河道生成完成后，选择距离出生点最近的河道中心线位置，以此为中心沿河长各覆盖 60 米，总长约 120 米。两端各 12 米平滑过渡到原水面；若靠近河流端点，可见试做段相应缩短。

- 沿用已有河流方向、速度、水深和水面网格，增加随流向移动的粗细波纹及局部变化。
- 浅水提高透底感，随水深转为更深的青绿色；岸边加入断续泡沫，流速较快处增加少量碎泡。
- 子弹从上方穿入这段水面时，触发短促水冠、飞散水滴以及向外扩散的两道涟漪。强度随弹速与入射角作小幅变化。
- 保留河床、岸边生态、地形编辑和存档；这轮没有迁移为 WaterBody，也没有加入游泳、浮力或脚步涉水。

## 接入

`TemperateHillsWorld` 的新增软引用随现有丘陵地表加载批次加载。在河道规划完成、地表开始提交前，由 `URiverPilotFXSubsystem` 创建共享水面动态材质和固定水花组件池。

现有水面没有阻挡碰撞。`FPlan::IntersectWaterSegment` 用与 `BuildWaterMesh` 相同的横断面顶点和三角形计算弹道穿越水面的位置，先通过现有 64 米空间桶缩小候选范围。弹道查询端点裁切到本段实际阻挡命中位置，避免在墙后产生水花；每发子弹只记录一次入水反馈。填高至水面之上的河床位置不触发击水。

子弹继续沿用原伤害、衰减、穿透和停止条件，水面反馈不增加弹道阻挡。试做段内命中水下河床时，屏蔽原本的干燥地面撞击反馈；其他目标仍走原有命中接口。

## 预算

- 预建 12 个可复用 Niagara 组件，退出丘陵世界时释放。
- 单次水花 14 个水滴、3 个水冠粒子，世界空间弹道运动。
- 水面保留最近 8 次入水涟漪，每次最长 1.8 秒。
- 瞬时预算 6 次，按每秒 30 次补充；超额命中只消耗该子弹的入水标记，不重复触发。

以上是实现上限，不是实测性能结论。没有为此增加实时网格流体求解器。

## 文件与素材

新增并保存于 `/Game/Fluids/RiverPilot20260923/`：

- `M_RiverPilot`：从当前 `M_RiverFlowWater` 复制，保留原图并混合局部升级层。
- `M_RiverDrop`、`M_RiverCrown`：程序生成轮廓的受光透明水滴、水冠材质。
- `NS_RiverBulletSplash`：水滴与水冠两组发射器。

复用项目已有 WaterMaterials 的水面、泡沫纹理与 Vefects 的 Niagara 发射器结构。新水花系统移除火焰发射器原有运动和视觉逻辑，使用本轮编写的运动、轮廓和透明度表达式；不新增外部付费依赖，也不覆盖来源资产。

制作脚本：`Tools/Fluids/author_river_pilot.py`。材质源代码与资产清单：`SourceAssets/RiverPilot20260923/`。必要 Niagara 编译中将 CPU VM 不支持的 `smoothstep` 表达式改为同等三次插值后，脚本完成保存并正常退出；材质中的 HLSL `smoothstep` 保留。

运行代码主要位于 `WorldGeneration/RiverPilotFXSubsystem.*`、`TemperateHillsRiverIntersection.cpp`，并接入 `TemperateHillsStreaming.cpp`、`TemperateHillsWorld.h`、`TemperateHillsRiver.h`、`Weapons/FPSBallisticsComponent.*`。

## 交付状态

- 四项资产已实际保存，记录：`SourceAssets/RiverPilot20260923/assets.json`、`authoring-r3.log`。
- 用户关闭编辑器后执行 `Tools/Build/Build-Editor.ps1` 成功，日志为 `Saved/BuildEditor/build-20260923-232300.log`。UBT 报告 `Target is up to date`、`Result: Succeeded`，本次调用没有重新编译动作。下一次用户启动项目时加载当前构建产物。
- 未主动启动编辑器界面或游戏，未进行实机、视觉、性能测试或回归。完成编译后的水面和击水观感由用户测试。

## 用户反馈无水花后的接入修复

2026-09-23：用户在丘陵试射时没有看到水花。定位到两项默认软引用只有包名，缺少对象名：

- 材质应为 `/Game/Fluids/RiverPilot20260923/M_RiverPilot.M_RiverPilot`。
- 水花应为 `/Game/Fluids/RiverPilot20260923/NS_RiverBulletSplash.NS_RiverBulletSplash`。

UE 的 `FTopLevelAssetPath::TrySetPath` 将不带点号后对象名的路径解释为包引用，`FSoftObjectPath::ResolveObjectInternal` 按该路径寻找对象。因此即使包加载完成，两个 `TSoftObjectPtr` 的类型化 `Get()` 也取不到目标材质与系统；原 `BindRiver` 会因空对象直接返回，既没有创建水花池，也没有应用试做水面。

修正默认对象路径，并在开始加载前只迁移这两个已知错误的旧引用，兼容编辑器可能已经保存过它们的关卡实例。加载回调现在确认两项类型化对象，失败时输出具体路径并显示加载失败原因。初始化成功后只记录一次 `RIVER_PILOT ready`，包含该存档种子、测试段中心厘米坐标及水花资源路径，便于定位。

原生构建成功：`Saved/BuildEditor/build-20260923-234451.log`，包含 `RiverPilotFXSubsystem.cpp`、`TemperateHillsStreaming.cpp`、`TemperateHillsWorld.cpp` 的编译与 `UnrealEditor-FPSGAME.dll` 链接。沿用已保存的四项资产，本次没有重新制作粒子。未启动游戏、PIE 或视觉测试；修复后的实际观感仍待用户确认。
