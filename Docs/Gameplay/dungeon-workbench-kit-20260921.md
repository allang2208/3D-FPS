# 地牢工作台组合 / 2026-09-21

工作台已由逐件摆放转换为一个可移动、旋转和重复放置的 Blueprint 组合。瓶子与桌角修订于 2026-09-21 23:42:50 保存到 `L_Dungeon_Prototype`，当前 Actor 为 `DGN_WorkbenchKit_Main`，采用“使用中”版本。未主动运行 PIE、截图、渲染或额外测试；实际视觉与碰撞效果由用户查看。

## 直接使用

在 UE 内容浏览器进入：

`/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Blueprints`

| Blueprint | 布置与材质 | 台灯 |
| --- | --- | --- |
| `BP_Workbench_InUse` | 保留当前完整工具陈设，轻微积灰 | 开 |
| `BP_Workbench_Idle` | 减少两件桌面工具，调整扳手与螺丝刀位置，增加积灰 | 关 |
| `BP_Workbench_Abandoned` | 减少部分墙面及桌面工具，保留空挂钩，增加旧化 | 关 |

将任意一个 Blueprint 拖入场景即可整组摆放。三个版本共用局部坐标网格，瓶子与桌角修订后为 29 个组件，普通 UE Actor 可按 Blueprint class 生成，运行时不依赖 Python。此次未接入随机地牢的自动选型逻辑。

原来的 24 个网格 Actor、一个电线 Actor 和一个实际灯光 Actor 已由组合替换；旧源资产保留。货架、白板、左侧工具柜、房间结构及其他灯光保持当前场景状态。

## 组合结构

- `AssemblyRoot`：整体摆放，默认前方为局部 `-X`，靠墙方向为 `+X`。
- `FrameRoot`：桌架和从插座到台灯的主电源线。
- `TableRoot`：桌板、划痕、抹布、保留零件和桌面 Fab 工具。
- `WallRoot`：工具板、工具、挂钩、零件抽屉、标签和插座。
- `LampRoot`：台灯、随灯臂移动的细线及实际光源；随 `TableRoot` 升降。
- `Anchor_*`：灯座、电线入口、插座出口和两个工作区域的命名连接点。
- `SupportArea_Main/Return`、`OperatorClearance`：仅编辑器显示的支撑与操作范围，无运行时碰撞。

全部几何已去掉原房间世界坐标，使用局部枢轴。单件桌面工具和两个瓶子采用接触底面作为 Z 基准，变体旋转围绕自身进行。灯罩沿用上一轮模型；桌板转角按后述修订闭合。

## 后续修改入口

根目录：`SourceAssets/DungeonWorkbenchKit20260921`。

常用调整只修改 `Config/workbench.json`：

| 字段 | 用途 |
| --- | --- |
| `table_height_cm` | 桌面高度，默认 93.9 cm；更新时桌面、工具、布和台灯随之升降，桌架调整支撑高度 |
| `supports.Main.y[1]` | 主桌后端，当前 259 cm；桌板、桌架、端部磨损和后排固定螺钉同步延伸 |
| `supports.Return.x[1]` | 回转桌内端，当前 -93 cm，与主桌边沿接合；保留窄木板拼缝 |
| `anchors.LampBase` | 灯座在组合内的基准位置 |
| `anchor_offsets_cm.LampEntry` | 相对灯座的电线入口偏移 |
| `anchor_offsets_cm.SocketExit` | 相对工具墙根节点的插座出口 |
| `power_cable.diameter_mm` | 主电源线直径，默认 5 mm |
| `power_cable.surface_clearance_mm` | 平放主线与桌面的净间距，默认 3 mm |
| `variants.*.omit` | 各版本不显示的组件 |
| `variants.*.tool_offsets` | 工具的局部移动量与旋转角 |
| `variants.*.dust/roughness_bias/surface_tint` | 各版本积灰、粗糙度和整体色调 |
| `placement.variant` | 当前地牢工作台采用哪个版本 |

台灯自身细线目前为已整理的 3.3 mm 模型。灯臂姿态与细线形状作为配套源资产保存；修改灯臂造型时仍需同时修改这组模型。`arm_diameter_mm` 是规格记录，不是当前导出器的在线建模参数。

高度与连接点修改通过制作入口重新生成相关内容，不是游戏运行时的动态伸缩。电源线根据支撑高度、线径、净间距及连接点重新生成 Bezier 路径。当前适配的是这张 L 形桌的布局，改桌面宽度、形状或大幅移动插座时，还需调整支撑区和路由控制点。

`Config/sources.json` 记录最终选用的源模型、对应旧 Actor 和材质来源。`Config/surroundings.json` 记录工作台之外现有工作间陈设，用于整套地牢重建，普通工作台更新不会执行它。

`Config/surrounding-sources.json` 记录房间 Blender 源的周边替换。2026-09-22 的货架盘线、贴条及随机料箱陈设已接入此配置，说明见 [货架修订](dungeon-workshop-rack-polish-20260922.md)。

## 一次更新的操作

使用项目 Python 执行：

```powershell
& 'C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe' 'D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkbenchKit20260921/Scripts/build.py'
```

可选参数：

- `--materials-only`：只调整材质或布置方案时使用，跳过 Blender 几何制作。
- `--assets-only`：只制作外部资产与配置，不连接编辑器。
- `--assemble-room-source`：同时更新完整房间的 Blender 源文件。

导入通过项目 MCP 桥批次互斥执行。编辑器需要已开启且不在运行游戏，存在未保存地图时保留现场并停止接入。脚本不会启动 PIE、执行测试、截图或渲染。

模型以几何、法线、UV、顶点色和材质槽的内容摘要决定是否重新导出/导入；材质实例与蓝图以配置摘要决定是否更新。更改磨损参数不要求重做模型，更换一个组件也不需要执行历史工作间优化脚本。

当前地牢实例的已有位置和旋转在更新时保留；`LayoutLocked` 标记用于后续装配系统识别固定摆放。本轮没有添加自动随机重排。

## 材质和源文件

材质主要收敛为三个共用父材质：

- `M_WBK_Surface`：喷漆、金属、橡胶及陶瓷等使用同一套可配置 PBR 输入。
- `M_WBK_Wood`：保留扫描木纹与局部使用痕迹。
- `M_WBK_Tools`：保留 Fab 工具原有的新旧贴图混合。

三个版本各自使用材质实例。印刷标签、蒙版材质与少数细小覆盖层保留原有专用材质。普通调整在实例中处理 `SurfaceTint`、`DustAmount`、`SurfaceRoughnessBias`；需要长期保存的修改同步记录到配置，避免将来更新覆盖。

- 独立组合可编辑源：`Authored/DungeonWorkbenchKit.blend`。
- 完整房间可编辑源：`Authored/DungeonRooms_WithWorkbenchKit.blend`。
- 局部网格与装配数据：`Authored/manifest.json`。
- 后续程序装配可使用的类路径与占地：`Authored/runtime-catalog.json`。
- 修改前地图备份：`Sources/L_Dungeon_Prototype_before_kit.umap`。
- 导入、蓝图编译与地图保存回执：`Receipts/bridge-install3.txt`、`asset-import.json`、`blueprints.json`、`scene-install.json`。

`DungeonAtmosphereV2_20260921/Scripts/install_v2.py` 在组合已建立后使用当前工作间定义，跳过之前六轮工作间优化阶段的顺序重放。本次未执行整套地牢重建。

本轮完成资产制作、必要导入、三个 Blueprint 编译和地图保存。以上不是实机视觉或性能验收结果。

## 瓶子与桌角修订

- `Bottle_OilCan`：淡灰绿色涂装金属油壶，补充底部卷边、密封圈、细齿瓶盖、金属出油嘴和开口。表面分别表现漆膜、局部露底、金属拉丝及轻微使用划痕。
- `Bottle_Degreaser`：暗红色 HDPE 清洁剂瓶，补充圆滑肩部、塑料分模线、防拆环和细齿瓶盖。与金属油壶使用不同的颜色、粗糙度和法线纹理。
- 标签为沿瓶身轮廓制作的曲面，距表面 0.12 mm，去掉旧瓶体和悬空平板标签。原创版式包含品名、用途、规格、容量、批次及维护说明；不使用真实品牌标识。
- 主桌后端从组合局部 Y=226 cm 延长到 259 cm；回转桌内端从 X=-95 cm 调整为 -93 cm。两张台面的后沿相齐，消除转角开口，台面高度仍为 93.9 cm。桌架、后排螺钉和端部磨损同步，木纹保持物理尺度。
- 两瓶从混合零件网格中拆出，各自成为可替换组件；贴图与参数仍共用 `M_WBK_Surface`，使用中、闲置、废弃三个版本沿用各自旧化参数。

制作入口已包含 `prepare_bottle_materials.py` 和 `author_bottles.py`。可编辑瓶子源为 `Authored/DungeonWorkbenchBottles.blend`，原始贴图为 `Authored/Textures/Bottles`，其材质配方为 `Authored/bottle-materials.json`。既有工具的 UV、材质槽和面角法线在移除旧瓶子时保留。源模型和房间组合已重新导出，本轮不执行测试、截图或验收渲染。

本次接入更新 6 个网格、复用 23 个，三个 Blueprint 已编译保存。地图保存回执为 `Receipts/bottle-install-save4.txt`；当前地牢实例位置与旋转保留。更新器同时处理蓝图重新实例化产生的当前地图独立 Actor（OFPA）待保存包，避免普通组件更新停在地图保存之前。
