# 建筑预览、自由放置与支撑图

## 本轮行为

- V 进入建筑模式默认开启吸附；F 切换吸附／完全自由位置。自由模式的原点使用射线命中产生的连续世界坐标，方块尺寸仍为 20×20×20 cm，不会在确认时重新量化到世界网格。
- 吸附到已有自由建筑时沿用该建筑的原点和局部 20 cm 网格；自由放置新建一个有稳定 GUID 和连续原点的体素体积。同一次地板／墙面刷子的各格共用体积，继续合并表面和圆滑边缘。
- 预览 Actor 独立可见。原预览组件归属 Controller，而 UE `Controller.cpp` 构造函数 `SetHidden(true)` 会隐藏其拥有的渲染组件，这是旧预览不可见的代码原因。新预览显示实际刷子体积，可放置为绿色，不可放置／无命中为红色。
- 新预览材质为 `/Game/Building/Voxels/Rounded/M_Voxel_PlacementPreview`，自发光、较清楚的填充与网格线；红色重叠预览不被目标墙体遮掉。关闭建造、打开其他菜单或卸载控制器时隐藏／销毁预览。

## 旧 Godot 依据及移植边界

本次实际读取 `archive/godot-before-ue5-20260910` 标签中的[Godot 支撑图](https://github.com/allang2208/3D-FPS/blob/archive/godot-before-ue5-20260910/scripts/building/support_graph.gd)及相关实现：

- `scripts/building/support_graph.gd`：地基锚点、只向上与横向传播、最多 4 个旧 50 cm 单元即 2 米横向跨度，非承重构件不继续传播。
- `scripts/building/build_system.gd`：底面四角采样、放置前计算支撑、拆除前判断剩余结构、受击破坏后的失去支撑清理。
- `scripts/building/build_piece_definition.gd`：`supports_weight` 和 `requires_full_base_support` 的数据责任。

旧 Godot 的 F 只取消同类构件自动朝向，仍使用格坐标；本轮按用户明确选择扩展为真正的自由世界位置。

UE 采用相同的支撑传播规则，默认横向累计 200 cm，20 cm 单元对应最多 10 格水平跨度。垂直对齐向上传播不增加横距；自由方块上移同时发生水平偏移时计入该偏移距离，避免斜着抬高无限延长悬挑。支撑不会向下传播。

自由／网格建筑之间按实际世界空间接触连接图：面间容差 0.2 cm，至少有 100 cm² 接触面积（20 cm 面的四分之一）；仅顶点、边线或很窄的接触不提供承托。直接地基需要底面四角的真实场景采样，忽略角色、本建筑碰撞和模拟物理的物体。允许首层体素部分进入坡地，沿用原有体素地面约定。

这是游戏性的支撑图与跨度规则，不是重量、应力或吨位模拟。已接入放置、拆除和撤销；主动拆除导致此前受支撑结构悬空时拒绝操作。当前木材、石头默认可传递承重，配置为 `FVoxelBuildMaterial.bSupportsWeight`，全局跨度为 `UVoxelBuildPalette.MaxCantileverCm`。

本轮未增加建筑耐久、受击破坏／自动坍塌、地形开挖或材料收费。旧 Godot 的这些相邻功能不宣称已经迁移；当前地图地形不在建造过程中动态编辑，地基结果在载入及涉及单元编辑时采样并缓存。

## 所有权、存档与事务

`AVoxelBuildWorld` 统一拥有原网格与自由体积、碰撞与显示分块、支撑图和编辑历史。`UVoxelBuildComponent` 持有预览 Actor、位置与吸附状态，控件只读取模式及判定信息。保持 Standalone 单机规则。

SaveGame v2 增加 `FreeVolumes`，每个记录包含 GUID、`FVector Origin` 和局部格坐标／材料表；原 `Cells` 字段、20 cm 格距及存档槽不变，仍读取 v1。吸附开关为建造会话状态，每次重新进入默认开启，不写世界档。

加载先恢复所有体积，再构建跨体积支撑图和网格。旧存档中缺支撑的建筑保留并提示，不在升级加载时自动删除；不能靠缺支撑的旧建筑无限延伸。编辑将重叠、场景碰撞与完整试算后的支撑判定通过后写入同一个世界 SaveGame；保存失败恢复原单元状态。撤销也经过相同检查，保留自由原点，不将其转回世界网格。

## 开发交付记录

操作与 UI 规划见 `Docs/UI/voxel-build-plan-20260913.md`。必要编译、预览材质制作记录位于 `Saved/VoxelPlacementSupport20260913`。本轮不启动游戏、不运行测试、不截图或渲染；由用户测试。

最终 Editor 构建完成，模块为 `UnrealEditor-FPSGAME-913603.dll`；预览材质作者脚本在独立宿主成功执行并返回 0，随后已导入正式 Content。重启已打开的编辑器、重新进入游戏世界加载新原生类型和资源。

预览材质在最小制作宿主 `Saved/VoxelPlacementSupport20260913/AssetAuthor` 中生成，作者脚本成功退出后按原包路径复制进正式 Content。宿主只用于避开本工程并行构建的模块文件清理和制作进程的后台线程崩溃，不包含另一份玩法代码或游戏地图。
