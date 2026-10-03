# 新随机地牢灯光优化

## 实施范围

用户授权：按已提出的灯光分级、房间管理、范围/灯型调整和面板明细建议优化。目标为 `L_Dungeon_Randomized` 的 `AAuthoredDungeonGenerator`。旧的 `Source/FPSGAME/Dungeon/` 生成器不在本轮范围。

此前保存的种子 92247 布局包含 66 模块、92 盏生成灯（30 盏走廊灯），是目录/布局总量，不是每帧提交数量。没有本轮地牢 GPU 分阶段基线，不能据此承诺帧数或毫秒收益。

## 已完成源码

### 生成灯策略

- 每个模块按原始强度稳定排序，最亮两盏为 key；Transit 为 corridor；其余为 fill。单灯模块继续保留主阴影灯。
- key 保留点光源及原有强度、颜色、衰减半径，显示距离 24 m / 淡出 5 m。
- corridor 改为朝下的 80° 外锥角聚光灯，保留原半径和阴影，显示距离 18 m / 淡出 5 m。
- fill 改为朝下的 65° 外锥角聚光灯，半径为原始值 ×0.8，上限 3 m，显示距离 14 m / 淡出 4 m。
- spot 的流明乘以 `0.5*(1-cos(OuterCone))`，与本机 UE 点光/聚光亮度换算一致，避免把点灯总流明直接塞进光锥造成中心过亮。发光半径保持 5 cm；聚光的 source length 为 0，避免旋转后长灯源穿过天花板。灯具网格继续保留。
- fill 仅在其横向影响范围能放入占地 cell（预留 35 cm 墙体余量）时关闭阴影；靠墙或窄空间的补光继续投影。该规则为几何保守限制，不是内部物件遮挡实测，也不保证每房严格两盏阴影灯。
- Fixtures / Debris 默认关闭网格投影。Shell、Floors、Ceilings、Frames、Services、Bridge 等不改，流体继续无阴影。没有修改碰撞、模型、材质、起始区域、曝光、Lumen 或全局画质。

现有地图内嵌的旧目录在原生生成路径中直接应用这些默认值，无需重写地图。支持目录逐灯 `role`、`type`（point/spot）、`outer_cone_degrees`、`optimized_radius_cm`、`max_draw_distance_cm`、`fade_range_cm`、`cast_shadows` 覆盖；parts 可用 `cast_shadow` 覆盖。显式作者阴影设置优先。

### 房间调度

- 复用成功生成的占地 cell 与连接图；起始区域作为只含连接关系的虚拟模块，不接管它已有的灯。
- 游戏中每 0.1 秒读取玩家视图；按实际 cell 定位当前房间，保留穿过连接件可达的一层相邻房间，并保留视锥可能穿过的门洞链。
- 门洞链使用放宽的 AABB/视锥测试，不做射线遮挡，不声称是精确 PVS。这是保守候选，会保留一部分实际上不可见的灯；不隐藏房间几何或玩法对象。
- 离开候选集合后保留 1 秒，再用 0.8 秒熄灭；恢复候选后 0.35 秒亮起。强度稳定后不重复写渲染参数，熄灭结束设置组件不可见。
- 无玩家视图、无投影或玩家在生成范围之外时不执行房间裁剪，保留原生最大距离规则。重新生成/EndPlay 清理计时器和弱引用。编辑器预览不运行该定时器。
- `Dungeon.RoomLighting` 记录调度的主线程墙钟耗时，纳入原有长帧事件；它不是灯光 GPU 耗时。

### 性能面板与 JSON v7

- 新增只读灯光栏目，复用已有面板刷新频率和主题，正文自动换行、随原页面滚动。界面最多列 12 盏，候选和启用优先，再按距离排序；完整灯列表导出，与网格 Top N 无关。
- 收集类型、所属模块/角色、移动性、强度与单位、位置/半径/距离、原始/缩放后显示距离、淡出范围、外锥角、阴影/体积阴影/散射及光追阴影配置。
- EnabledLights 要求组件已注册、可见标志、AffectsWorld 和 `ComputeLightBrightness>0`；兼容 EV 的零/负数和 IES，不能只按原始 Intensity 是否大于零判断。
- 旧 VisibleLights/ShadowLights 保留原来的“注册与可见标志”语义；新的视野候选与摄像机所在球形范围重叠都是估算，不是实际渲染计数。
- 记录灯光相关 CVar 快照，缺少值为 null；配置不能证明某个 GPU pass 实际执行。
- 实际渲染灯数及局部照明、阴影、Lumen、体积雾 GPU 分段仍未采集：JSON 为 null，面板明确显示未采集。SkyLight 不在本次局部/方向灯列表中。

## 开关与生效

- `fps.Dungeon.Lighting.Optimize 1` 默认开启；0 在下次生成恢复旧灯型、强度、范围及投影策略。更改此值不重建当前房间。
- `fps.Dungeon.Lighting.RoomCulling 0` 让当前优化生成的所有房间恢复启用；1 恢复房间调度，两者都通过渐变应用。
- 使用固定的 `DungeonSeed=92247` 才能与该布局作对照；两个随机种子、不同视角或此前的昼夜地图采样不构成 A/B。
- 常规 Editor DLL 更新后，重新进入随机地牢时执行新生成逻辑；既有编辑器视口里保存的预览灯不会因编译自动改变。

## 构建与测试状态

源码已完成。用户保存关闭后，一个进程卡在 Preparing to exit 超过 5 分钟；经用户明确授权，仅结束残留进程 87008。没有结束后来新启动的编辑器。

- 第一轮正常 Editor 构建：本轮地牢生成器、灯光调度、面板、采集与导出 C++ 均完成编译。修正了 UBT 报告的 AuthoredDungeonLighting.cpp 首头文件顺序。完整构建因并行变动的换弹接口、双持字段与已删除女巫源文件失败；未覆盖那些源文件。
- 第二轮重新构建：UHT 报 WitchRebuiltMonster 的 Placeable 与抽象父类 WitchMonster 的 NotPlaceable 冲突。之后该父类已由最新源码改为 UCLASS(Abstract)，本任务的预期文本补丁未匹配，没有修改女巫文件。
- 第三轮启动构建前：发现三个新项目编辑器进程（其中一个带 SourceAssets/GamedevPortal20260922/editor-import.log 启动参数），保留现场，没有开始第三次构建。

本任务尚未完成最后的全项目构建，不能据此宣称基础 DLL 已包含所有修改。编辑器关闭后仍需一次正常 Editor 构建。前两轮日志：

- `Saved/PerformanceDiagnosis20260922/build-editor-dungeon-lighting-1.log`
- `Saved/PerformanceDiagnosis20260922/build-editor-dungeon-lighting-2.log`

按用户规则未启动 PIE、游戏或运行自测。照明外观、门口淡变、薄墙/补光以及实际性能变化由用户测试。MegaLights 与 GPU pass 实测采集尚未实施。
