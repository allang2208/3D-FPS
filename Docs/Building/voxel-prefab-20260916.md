# 建造面板与构件放置（2026-09-16）

用户要求：先把建造面板做成与背包同款的右侧抽屉，并接到屏幕最右边；随后「选中 prefab → 按 20 cm 网格生成单体（碰撞／旋转／拆除）」。面板规划见 [建造面板规划](../UI/voxel-build-panel-plan-20260916.md)。

## 面板

`UVoxelBuildWidget` 从「右上角几行文字」改为右侧抽屉：贴屏幕最右、上下 12px、宽度为视口 48%（钳制 720–1040px），用 `FMath::FInterpConstantTo(DrawerProgress, Target, Delta, 4.0f)` 与 `SetRenderTranslation((1 − 进度) × 宽度)` 开合，和 `ColdSteelHUDWidget` 的背包抽屉同一节奏与同一玻璃参数（真实 `UBackgroundBlur` 强度 9／半径 21、`GlassTint` 248/255、圆角 10px、1px 细边 6px 滚动条）。

内容为「材质／构件」两分类＋卡片列表，数据来自 `DA_VoxelBuildPalette`：材质卡显示名称与稳定 ID，构件卡显示名称与 `Footprint × 20 cm` 尺寸。页脚按键说明同步改为面板／建造两阶段写法。

### 两阶段交互（2026-09-16 修正）

用户实测后指定：**打开面板就切到鼠标模式，不再影响游戏里的操作（尤其是视角）；选完要建造的物体才切回游戏建造**。

| 阶段 | 输入 | 表现 |
| --- | --- | --- |
| 按 B | `SetPanelOpen(true)`：`SetIgnoreMoveInput/SetIgnoreLookInput(true)`、`bShowMouseCursor=true`、`FInputModeUIOnly`（焦点给抽屉） | 抽屉滑入，光标可用，鼠标不再转视角、不再放置；预览隐藏 |
| 面板中 | 点击卡片，或键盘 `1/2`（材质）、`3-9`（构件）、`0`（取消构件） | 选择走 `SelectMaterial`／`SelectComponent`，两个函数在面板打开时自动 `SetPanelOpen(false)` |
| 选完 | 恢复 `FInputModeGameOnly`、隐藏光标、清除忽略标志 | 立即回到建造：恢复预览与射线目标，左右键放置／拆除 |
| B 循环（2026-09-16 二次修正） | 建造中按 B → 回面板；面板中再按 B → 退出建造 | `bPanelOpen` 为真时 B 走 `SetBuildMode(false)`，关抽屉并归还输入 |
| 退出 | `Esc` 退一层（面板→建造→退出），或打开其他菜单、打开背包 | `SetBuildMode(false)` 同样恢复输入模式，不把光标状态留给游戏 |

键盘处理在两处同时生效且互为兜底：抽屉获得焦点时由 `UVoxelBuildWidget::NativeOnKeyDown` → `HandleDrawerKey` 处理，建造状态由 `HandleInput` 处理。两条路径的 B/Esc 语义完全一致，并用文件级 `DrawerKeyFrame`（`GFrameCounter`）记录抽屉本帧已处理的按键，避免同一次按下被执行两次（否则“面板中按 B 退出”会被立刻重新进入建造）。该守卫刻意不用类成员，以保持这次改动只是函数体补丁。

本轮改动**未做全量编译**：编辑器正在运行，通过编辑器内 `LiveCoding.CompileSync` 热补丁生效（`Saved/Logs/FPSGAME.log` 17:23:54 `Live coding succeeded`，无编译错误、无“需要重启”）。磁盘上的 `UnrealEditor-FPSGAME.dll` 仍是 17:13 的全量编译结果，关闭编辑器后热补丁不会保留，需要重新执行一次 `Build.bat FPSGAMEEditor Win64 Development`。

控件放在 z 序 21（高于 HUD 的 20），抽屉展开时覆盖右侧栏目入口；关闭后 `Collapsed`，不参与命中与 Tick。

## 构件单体

| 项 | 实现 |
| --- | --- |
| 网格吸附 | 命中点投影到 20 cm 格：`Cell = ToCell(命中点 + 法线 × 0.5)`，再按旋转后的 footprint 回退半宽，保证占位边缘落在 20 的倍数上 |
| 旋转 | `R` 每次 90°，`AVoxelBuildPrefabActor::RotatedFootprint` 交换 X／Y 占格；actor 用 `ComputeTransform` 以**包围盒中心**对齐，避免绕网格原点旋转后偏出格位 |
| 碰撞 | `AVoxelBuildPrefabActor` 自带 `UStaticMeshComponent`（Movable、`BlockAll`、`ECC_WorldDynamic`、关闭导航影响），并使用建筑的物理材质 |
| 拆除 | 右键命中构件单体即拆除，同时移除记录并重新计算占位 |
| 占位互斥 | 构件与体素互相阻挡：放置构件检查体素格与已有构件；体素放置／提交检查 `PrefabCells` |
| 存档 | 建筑存档升级到 v4，追加 `TArray<FVoxelBuildPrefabInstance>`（Id、锚点格、90° 档、footprint）。写盘先写版本号，读取时 `Version >= 4` 才读该字段，v1–v3 旧档仍按原字节长度读取 |
| 载入 | footprint 以调色板当前定义为准重新计算；调色板里已不存在的构件 ID 跳过并记警告，不让整档失效 |

## 边界

## 已接入的构件（2026-09-16）

活动调色板是 `UVoxelBuildComponent` 实际加载的 `/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette`。上午那次注册写进了父目录的初版调色板，活动调色板的 `components` 一直是 0，因此面板构件页为空；现已写入两根柱子：

| 稳定 ID | 名称 | 网格 | 20 cm 占格 | 材质 |
| --- | --- | --- | --- | --- |
| `roman_column` | 罗马柱 | `SM_RomanColumn_Detailed` | 4 × 4 × 13（＝80×80×260 cm） | `M_RomanStone_V2` |
| `baluster_small` | 矮栏杆罗马柱 | `SM_RomanBaluster_Small` | 2 × 2 × 5（＝40×40×100 cm） | `M_Plaster_Detailed` |

占格与网格包围盒逐轴相等，放置按 20 cm 吸附不会半格偏移。写入脚本 `SourceAssets/RomanColumn20260915/add_panel_components.py`，盘点脚本 `inspect_prefab_palettes.py`；调色板内容在进入建造世界时读取一次，已在 PIE 中需重新进入世界。

- 构件放置**不参与**支撑图与坍塌模拟，也不会因失去支撑掉落；体素与构件的接触不建立承重边。这是本轮的范围，不是完整支撑契约。
- `Ctrl+Z` 仍只撤销体素编辑历史，构件的放置与拆除不进入该历史。
- 面板卡片点击需要鼠标光标；建造模式保持游戏输入（准星瞄准／左右键放置拆除），因此游戏内用 3-9 选择构件。
- 本轮完成开发、资产沿用与必要编译：关闭编辑器后 `Build.bat FPSGAMEEditor Win64 Development` 返回 `Result: Succeeded`（面板初版模块 17:06 落盘，同一日按用户实测反馈修正两阶段交互后重编，17:13 再次落盘；中间尝试因编辑器 Live Coding 占用被拒）。仍未运行游戏、未截图、未做视觉与操作验收，由用户测试。

## 文件

| 文件 | 职责 |
| --- | --- |
| `Source/FPSGAME/Building/VoxelBuildWidget.h/.cpp` | 抽屉外壳、分类页签、卡片列表、开合动画、状态文本 |
| `Source/FPSGAME/Building/VoxelBuildComponent.h/.cpp` | 抽屉开关、材质／构件选择、构件预览与放置分支、按键 |
| `Source/FPSGAME/Building/VoxelBuildPrefabActor.h/.cpp` | 构件单体的网格、碰撞与旋转／对齐数学 |
| `Source/FPSGAME/Building/VoxelBuildWorldPrefab.cpp` | 构件校验、生成、拆除与占位索引 |
| `Source/FPSGAME/Building/VoxelBuildWorld.h/.cpp`、`VoxelBuildWorldSave.cpp`、`VoxelBuildPersistence.h/.cpp`、`VoxelBuildTypes.h` | 构件记录、存档 v4、体素与构件互斥 |
