# 温带丘陵植被初版

独立地图：`/Game/GameMaps/L_TemperateHills_Initial`。范围为 1.024 × 1.024 km，UE 5.8.2。

## 打开

主场景 `DayNight_Lighting` 开始游戏后，出生点前方偏右会生成绿色文字的 **TEMPERATE HILLS / Black Poplar** 门。靠近 2 米内按 **E** 进入；丘陵出生点前方的 **HOME / Main Map** 门使用同样操作返回。门户沿用现有场景门外观，运行时生成，不需要重新保存主场景。

本轮传送门改动包含原生 C++，已打开的编辑器需要重启后再开始游戏。

加载优化后，丘陵入口先异步预加载地图，门牌显示 `Preparing hills`，可按 Esc 取消。进入后屏幕左下角显示出生区域、草地、灌木、岩石和黑杨的加载阶段。出生区域碰撞就绪即可进入，随后继续加载植被；地图切换仍使用 UE 的 `OpenLevel`，不宣称整个过程完全无停顿。

首次从主场景进入时，没有丘陵世界存档就随机建立一个；之后往返使用原种子和世界 ID。传送时的 `HillsContinue` 地图选项优先于启动时的 `-HillsNewWorld` / `-HillsSeed`，避免返回后再次进门重建世界。若需要重新随机生成，请使用下面不带 `-Continue` 的启动脚本。玩家沿用本进程已有档案；从主场景进门不会切换为脚本专用的 `TemperateHillsStudy` 档案。

在项目根运行：

```powershell
& ./Tools/WorldGeneration/Open-TemperateHills.ps1
& ./Tools/WorldGeneration/Open-TemperateHills.ps1 -Continue
& ./Tools/WorldGeneration/Open-TemperateHills.ps1 -Seed 122
```

第一条建立随机种子的新世界，第二条沿用本样地上次的种子和世界 ID，第三条建立指定种子的世界。样地使用独立玩家档案 `TemperateHillsStudy`、世界槽 `TemperateHills_World`。标准 FPS 移动操作可在生成地面行走。

## 生成规则

1. 全局坐标与种子决定连续高度：大尺度起伏、扭曲丘陵、弯曲谷地、小尺度地表细节。地形按 64 m 格子流送，近处 2 m 顶点间距，远处 8 m；LOD 边缘用向下裙边覆盖接缝。全局高度函数和种子语义保持一致。
2. 启动先提交出生点周围 3×3 格，异步碰撞就绪后才生成玩家。高精度地形半径 160 m，已加载格保留额外 64 m 缓冲；粗地形半径 384 m，超出再加 64 m 才卸载。最多两个后台网格任务，每帧最多提交一个网格、卸载一个格子。只后台计算数值和网格，组件操作在游戏线程执行，碰撞使用异步烹饪。前方地形未就绪时暂缓角色移动。谷地和出生点周围保留空地。
3. 四层 PCG Graph 使用项目的 `TemperateHillsPoints` 节点输出带 `Mesh` 和 `CandidateKey` 属性的点，再接 UE 原生实例生成器。黑杨使用 Skinned Mesh Spawner；岩石、灌木和草使用 Static Mesh Spawner。关卡保存 PCG World Actor；运行时完成地形后明确注册各层执行源。
4. 黑杨使用 12 m 抖动候选网格与低频林地密度，拒绝陡坡、谷地和出生点；四种模型随机旋转、缩放。草、灌木、岩石采用独立种子盐和间距，避免贴近树干。
5. 树木/岩石/灌木/草的 PCG 网格分别为 64/64/32/16 m，生成半径分别为 180/120/80/45 m；清理半径为生成半径的 1.3 倍。格子使用半开边界，每个点只有一个所属格。生成草灌时缓存邻近树木候选，避免每个草点重复计算九次完整树木规则。
6. 草、灌木、岩石依次异步加载，然后分四批加载黑杨，最后加载雾体。`DA_TemperateHillsStreaming` 全部环境资源为软引用，地图不再直接拉入所有树木和贴图；完成的加载句柄在本世界内保留，离开后释放。树干碰撞仅在 96 m 内逐格建立，超过 128 m 逐格卸载。九个低雾候选点只激活 140 m 内最多三处，超过 180 m 卸载。地表仍混合草苔、草土和碎石，并读取现有天气管理器的地表湿度。
7. 本地图将 PCG 每帧时间目标设为 2 ms、同时生成组件上限设为 2、初始格子池设为 16；离开时恢复原值。正常游戏启动不再计算整片布局的审计哈希。上述时间是调度目标，不是实测帧耗时或加载速度承诺。

## 本次使用的资产

| 来源 | 选用内容 | 用法 |
|---|---|---|
| Megaplants: Black Poplar | `Tree_Black_Poplar_01_A/B/C/D` | 原生 Nanite 骨骼树木实例；资产没有 PhysicsAsset，样地单独生成轻量树干碰撞 |
| Normandy | `SM_Grass_00A/01A/02A`、`SM_GrassTall_00A` | 地表草丛 |
| Normandy | `SM_PlantTypeA/B/C_00A` | 林下灌木 |
| Normandy | `SM_LS_Rock_00A` 至 `03A` | 坡地岩石 |
| Normandy | `GroundGrassMoss/GrassSoil/RockyRoad` 三组贴图 | 本项目生成地形的独立材质 |
| Normandy | `BP_LocalFogVolume_Master`、`MI_VolumeFog_01A` | 独立稀薄低雾实例 |
| Military Trench / Industrial Infrastructure | 本轮未选用 | 当前纯自然样地没有需要接入的军事或工业设施 |

源包资产保持原样；只保存 `WorldGeneration/TemperateHills` 中本次生成的配置、PCG 图、材质、用于实例化的四棵树木副本，以及独立样地地图。没有复制源包示例关卡。具体引用由 `Saved/TemperateHills/authoring.json` 记录，原资产属性探查见 `source-probe.json`。

黑杨依赖引擎的 **ProceduralVegetationEditor** 插件内容：两个原始材质实例的父材质为 `/ProceduralVegetationEditor/SampleAssets/Materials/MasterMaterials/MA_Foliage_Trees`。工程已启用该插件及其声明的 DynamicWind 等依赖，以及 `r.Nanite.Foliage=1`（需要重启编辑器、首次编译对应着色器）。黑杨的枝叶使用 Nanite Assemblies/Voxels，普通 Nanite 开关不足以显示完整树冠，参见 [Epic 的 Nanite Foliage 说明](https://dev.epicgames.com/documentation/unreal-engine/nanite-foliage)。

本项目复制父材质、两个材质实例及四棵现有树木到样地目录，仅补充 InstancedSkinnedMesh 材质用途并重定向材质；几何和原始源资产不改动。UE 5.8 的 Skinned Mesh Spawner 尚未实现描述符材质覆盖，因此需要这层项目内副本。这里使用现有树型输出，不进行 PVE 树型重建；风动仍需单独视觉验收。

## 实现与复建

- `Source/FPSGAME/WorldGeneration/TemperateHillsWorld.*`：种子、地形、植被规则、玩家落地、碰撞、低雾与运行验证。
- `Source/FPSGAME/WorldGeneration/TemperateHillsStreaming.cpp`：分阶段加载、地形 LOD/碰撞流送、提交预算、就绪提示和附近树干/雾体。
- `Source/FPSGAME/WorldGeneration/TemperateHillsSurface.h`：后台任务使用的纯数值地形函数，不访问 Actor/UObject。
- `Source/FPSGAME/WorldGeneration/TemperateHillsPCG.*`：运行时 PCG 点数据。
- `Tools/WorldGeneration/build_temperate_hills.py`：UE Editor Python 作者脚本；先编译原生模块，再用独立命令行编辑器执行。
- `Tools/WorldGeneration/upgrade_temperate_streaming.py`：将已有地图切换到软引用配置并更新 PCG 网格与裁剪距离；保存修改前的地图副本到 `Saved/TemperateHills`。
- 旧 `HillsAudit` 保留作为初版开发记录入口，其“全图已生成”和全图碰撞断言不适用于本次距离流送模式；本轮未运行或追加测试。

在已恢复 Black Poplar、Normandy 资产并编译 Editor 模块的本机执行资产生成：

```powershell
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript -script='D:/FPS3D/FPSGAME/Tools/WorldGeneration/build_temperate_hills.py' -unattended -multiprocess -NullRHI -nosplash
```

Git 发布源码、作者脚本和说明。树木、贴图、引擎插件及生成的二进制地图/材质保留在本机，不随源码公开再分发；新机器需要先恢复相同内容依赖。普通启动脚本不会启用 `HillsAudit`，也不会自动执行测试。

## 初版边界

这是单机、可行走的植被样地。地形已按距离分块流送，并有近/远两档网格；植被使用 PCG 按距离调度。世界存档只保存种子、版本与世界 ID，尚无砍树、采集、建筑、怪物导航和这些行为的持久化。日夜天气与事件栏已接入，见[丘陵天气接入说明](../WeatherTemperateHills-20260912.md)；画面效果与树木风动由用户测试。地图边缘是样地边界，尚无正式世界边界玩法。

## 构建与交付状态

2026-09-12：Editor 与 Game 原生目标编译成功，作者脚本已生成独立地图、四层 PCG 和项目内资产副本。

在项目更新“由用户自行测试”的规则之前，开发运行曾完成 64 块地形、81 处高度碰撞射线、玩家落地、树干阻挡、候选点唯一性、存档读回和实例生成检查。种子 122 的采样地形高程为 37.390–76.310 m，黑杨实例数为 1,844；这些是此前开发运行的记录，不代表最终画面验收。

最后补充了 `r.Nanite.Foliage=1` 以开启黑杨依赖的 Nanite Assemblies/Voxels。发现项目最新规则后已停止自动运行，**此设置后的完整树冠、风动、新建随机世界与跨进程继续游戏尚未完成最终测试**。此前截图含不完整树冠，不作为最终效果图。首次打开需等待树木渲染数据和着色器编译；已打开的编辑器需要重启才能使用新设置。

2026-09-12 后续加入主场景 → 丘陵的入口门和丘陵 → 主场景的返回门。Editor 和 Game 目标编译成功；此传送门接入按项目规则未执行运行测试。

此地图已可从主场景传送门或上方启动脚本进入，尚未接入主菜单。完整大世界、性能及打包验收不属于本次已完成范围。

## 加载优化交付（2026-09-12）

针对用户反馈进门长时间卡住，已改为上述软引用、分阶段异步加载、近处优先地形流送、异步碰撞和有限 PCG 调度。保留现有树型、候选布局与世界种子，不降低全项目画质设置。

本轮只完成开发、必要构建和地图配置更新，按用户规则未运行游戏、自测、性能采样或截图。因此没有“加载减少多少秒”或 FPS 提升的实测结论；首次生成 Nanite 派生数据或编译着色器仍可能耗时。

Editor/Game 原生构建已完成。地图升级脚本已保存软引用配置、四张 PCG 图和地图，黑杨本轮 Nanite 派生数据也已在作者进程中构建完成。作者脚本执行成功；命令行编辑器最终因项目既有的 `GameFeatureData` 注册配置报错返回 1，该报错不在本轮修改范围内。相关过程日志位于 `Saved/TemperateHills-streaming-*.log`。
