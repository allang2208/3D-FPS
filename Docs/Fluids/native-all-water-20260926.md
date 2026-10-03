# Clearwater 已认可表现推广（2026-09-26）

用户认可 `L_ClearwaterWater` 候选效果，并明确要求推广到其他水体。本轮沿用已有河流、喷泉和地牢积水资产路径，不改变地图布局、碰撞、采集、弹道、伤害、存档、喷泉供水或地牢生成规则。

## 覆盖与适配

| 水体 | 运行主材质 | 本轮处理 |
| --- | --- | --- |
| 全丘陵河道 | `/Game/Fluids/RiverPilot20260923/M_RiverPilot` | SingleLayerWater；保留顶点 RG 流向、B 流速、A 水深与原岸边泡沫配方；谱波仅进入法线，避免粗河道网格位移破坏岸线 |
| 罗马喷泉各层池面，包括已放置及新建喷泉 | `/Game/Props/RomanFountain20260917/Materials/M_FountainWaveWaterV3` | SingleLayerWater；保留原池面位移及对应法线，叠加低强度谱波；共享击水和尾流 |
| 已有与生成地牢薄积水 | `/Game/Dungeons/AtmosphereV2/GateWater/Materials/M_Dungeon_ShallowPuddle` | SingleLayerWater Masked；顶点 R 控制轮廓、边缘反射与波纹，保留滴水细纹，不抬高水面；谱波强度仅 0.045 |
| Clearwater 候选关卡 | 原已认可 Native 材质 | 保持已认可资产及独立水下组件；共享水下组件不再覆盖该水面 |

喷泉水柱、水帘、飞溅和溢流薄片继续使用已认可的 Niagara／透明效果，它们不具备水平水面与水下体积，不套 SingleLayerWater。角色击水、水花冠、自然图集与原限流保持原实现。

## 光学、焦散与水下

- 全部水平水面采用同一套已认可的每厘米吸收、散射及相位参数，原假天空发光退出水面输出；实际反射与照明由 UE 水渲染路径承担。
- 共用现有 32 帧、4096×2048 焦散图集。利用 `SceneDepthWithoutWater` 和像素深度重建水下接收位置，把动画焦散连接到 `ColorScaleBehindWater`；河床、石质池底和地牢地面保留各自材质、光照及阴影。每像素最多两次图集采样；远距衰减，未新增 RT 或全场地面材质替换。
- 焦散仍是已有离线序列的光学近似，非实时 FFT 聚焦；薄积水依实际深度自然减弱，不做发光亮斑。
- `URiverPilotFXSubsystem` 新增私有光学实现 `RiverNativeOptics.cpp`。原有注册阶段收集最多 8 个方向光，生成事件追加登记；每 0.25 秒选择有效主光并更新河流及 95 m 内已注册静态水面参数，夜晚与无方向光室内关闭太阳焦散。水面本身继续响应场景局部灯。
- 一个世界共用一个异步加载的水下 MID 和后处理组件，复用已认可 `/Game/Clearwater/MI_ClearwaterUnderwater`。30 Hz 查询当前本地相机；河道使用现有空间索引与实际地形底面，静态池面使用原多边形轮廓及分层高度。喷泉局部体积上限 120 cm、薄积水 2 cm，再以一条共享预算内碰撞查询阻止穿过池底／立柱的误染色。没有入水时立即归零；入水沿 12 cm 过渡带平滑混合。
- 单玩家表现逻辑；不新增游泳、浮力、多人或分屏相机同步。退出世界取消加载、清除计时器与事件并销毁自有后处理组件。

## 源与生产入口

- `Tools/Fluids/native_water_surface.py`：只增加／更新 `NativeWater20260926.*` 节点，保留原图与可恢复输出；更新同一个共享击水节点，不清空已有材质表达式。每个目标修改前保留原包，编译后保存指定包。
- `SourceAssets/NativeWaterAll20260926/CausticsBehindWater.hlsl`：接收深度、太阳方向和图集投影。
- 原河流作者 `author_river_pilot.surface` 与静态水面 `augment_static_surface` 已接上本层，因此喷泉／地牢原制作器以后重建时继续应用本轮光学。
- 新运行逻辑依附原 `RiverPilotFXSubsystem` 的初始化、注册和清理；原 12 个水花池、8 个击水槽、4 个尾流槽及限流保持不变。不在热路径同步加载资源、读回网格或扫描全世界 Actor。

## 本轮状态

- **源码与基础 DLL 已完成**：用户保存关闭编辑器后，`Tools/Build/Build-Editor.ps1` 完成 60 项编译／链接，`Result: Succeeded`，耗时约 53 秒。日志：`Saved/BuildEditor/build-20260926-193229.log`。
- **三类材质已实际保存**：`M_RiverPilot`、`M_FountainWaveWaterV3`、`M_Dungeon_ShallowPuddle` 均完成最终 SM6 材质编译（返回空错误列表）和指定包保存。回执：`SourceAssets/NativeWaterAll20260926/assets-saved-20260926_193524.json`；后台制作日志：`Saved/NativeWaterAll20260926/author-commandlet-02.log`，进程退出码 0。
- 更新原有主材质路径，因此引用它们的已放置场景、运行生成河道、新建喷泉和地牢装配均沿原引用获得本轮效果，无需重建地图或覆盖用户存档。
- 原资产包备份：`SourceAssets/NativeWaterAll20260926/BeforeNative_20260926_193524/`。首次 commandlet 在顶点色接线处停止，未保存目标；已改为显式组合顶点 RGB 与 Alpha，保留河流水深和积水边缘数据。第二轮构建图时出现的中间态缺输入／缺水体输出节点告警发生在最终接线及编译前，不是保存后的编译错误。
- 未打开交互式编辑器，后台制作完成后未启动游戏。此前活动编辑器桥不可连接，未通过该桥改写本轮资产。

未运行游戏、PIE、截图、运行测试或性能采样；用户认可的是上一轮候选，本轮推广的观感和实际性能仍由用户测试。
