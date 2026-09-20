# 丘陵升级发布与本机恢复（2026-09-20）

本次整理本对话的河岸生态、卵石地面、树木再生、DayNight 天空复用，以及地表材质优化和附近优先加载。发布源码、作者脚本、技能与文字记录；不发布 Content、第三方原始素材、缓存、日志、DLL 或 trash。

## 发布内容

- 河道保留既有排水中心线，增加非对称宽度、弯道内外岸、纵向平滑、岸滩起伏，以及水面流向/速度/深度顶点数据。河岸草地过渡、卵石分布与材质遮罩保持一致。
- 补齐树木再生与采集表现的接入；继续沿用已有再生存档/时间实现，PCG 不再重复生成已经由生长系统持有的树。默认砍倒后休眠 1 个游戏日、第 6 个游戏日成熟（休眠包含在完整周期内），具体规则见已有再生文档与代码。
- 接入 DayNight HDR 天空材质、异步资源加载和退出清理；沿用现有昼夜与天气时间源，不导入演示场景。作者脚本保留原太阳圆盘、云层、HDR 有限值处理及既有闪电材质接入。
- 地表作者脚本统一高度步进/显示投影，修正法线混合，增加近景交点细化、干壳随机平铺和读取前分支。
- 地面加载跟踪实际共享贴图的 mip，修正完整着色器变体等待；进入前要求附近约 96 m 的地形与碰撞，远处地形进入后继续按原预算流送。

此前已发布的 `TemperateHillsRiverEcology.cpp`、`TemperateHillsPebbleShore.cpp`、`TemperateHillsDayNightSky.cpp`、`ProductionTreeGrowthPresentation.cpp` 和 `ColdSteelTreeGrowth.cpp` 继续作为实现的一部分。本次补齐与它们关联的声明、加载和生命周期调用；没有把其它武器、UI、怪物的未提交修改并入发布。

## 素材恢复与作者顺序

从有授权的完整本机工程恢复 `Content/WorldGeneration/TemperateHills`、`Content/GameMaps/L_TemperateHills_Initial` 及原有依赖，保持 `DA_TemperateHillsStreaming` 引用。关键运行资源为：

| 用途 | 路径/来源 |
| --- | --- |
| 当前地面 | `/Game/WorldGeneration/TemperateHills/PebbleShore/M_PebbleShoreGround`；基础为同根 `M_TemperateGround` |
| 四层地面源 | PN_GrassLibrary 的 ground_I；UnrealNormandy 的 GroundSoilExcavated、MossyGravel、GroundDry |
| 河岸与卵石 | TemperateHills/PebbleShore、RiverEcology；已导入的河岸扫描贴图和 WaterMaterials 圆石 |
| 河岸草本与乔木 | 原有 Fab 植物、河岸生态和四个树变体；准确来源见下列生态文档 |
| HDR 天空 | TemperateHills/Sky/M_HillsDayNightSky、MI_HillsDayNightSky；源 PWL_Light_Manager 的四时段 HDR |
| 体积云与闪电 | 项目已有 Weather/Materials 及 `build_layered_cloud_material.py`、`build_storm_lightning_materials.py` |

这些源包和派生 uasset 的本机使用权不等于公开原始资产的再分发权，本次不改变原许可边界。来源与参数分别见 [河岸与再生](river-ecology-tree-regrowth-20260913.md)、[密集河岸](dense-riverbanks-20260914.md)、[卵石地面](pebble-shore-20260914.md)、[HDR 天空](hills-daynight-hdr-sky-20260915.md)。

当前地表唯一最终作者入口是 `Tools/WorldGeneration/build_hills_ground_v2.py`。先恢复所需扫描纹理、圆石和配置，再在当前编辑器通过项目桥执行该脚本；河流生态制作链为 `build_temperate_river_ecology.py` → `build_dense_riverbanks.py`。不要在最终地表重建之后重跑旧地面图。

`build_temperate_hills.py` 的旧三层地面段、`build_pebble_shore.py` 的旧河岸材质段已被替代，但脚本还保存初始建图、PCG、扫描导入和圆石资产制作的独有过程，因此保留为恢复参考，不能整份当作废案移走。它们不是当前地表更新入口。

## 归档

两份新版本制作前的旧地面材质快照，从 `Saved/GroundMaterialOptimization20260920/BeforeAuthoring-20260920-000955-117411` 移至本机 `trash/hills-ground-superseded-20260920`，合计 116,546 字节。当前 Content 正式材质不移动。

逐文件原路径、目标、大小、SHA-256、替代物与原因见 [归档清单](../AssetArchives/hills-ground-20260920.json)。移动前确认路径范围，移动后散列一致。`authoring.json` 中的旧备份路径是制作当时的记录，现在按归档清单定位；诊断脚本和日志仍保留本机作为证据，不当作废案删除。

## 技能及验证边界

可复用经验进入 `ue5-debug-validation/references/dynamic-terrain-material-loading.md`，包括按需 shader map、世界坐标采样的 mip 驻留、附近就绪与后台流送边界，以及 POM/法线/分支采样注意事项。个人技能和工程镜像的本次新增内容同步，保留两处既有的其它内容。

最近一次必要 Editor 构建为 `Saved/BuildEditor/build-20260920-140931.log`，地形源码编译及 Editor DLL 链接成功。它证明本机当时工作树完成构建，不代表本次 Git 整理另做了游戏测试。加载修复后的实际时间、清晰度和 GPU 性能尚待用户实测，详见 [加载诊断](ground-loading-diagnosis-20260920.md)。

本次按用户授权执行仓库整理与推送前的路径、暂存差异、空白错误、大小、敏感信息、许可范围和远端检查；不启动 PIE、不重建材质、不重复原生构建或追加玩法验收。
