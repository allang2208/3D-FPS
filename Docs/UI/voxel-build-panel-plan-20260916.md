# 建造面板规划（2026-09-16）

## 目标与交付阶段

- 名称、入口、解决的操作需求：右侧「自由建造」抽屉，按 **B** 开关（Esc 也可退出）。玩家在建造时看得见当前材料／构件、放置反馈和全部按键；构件不再只能靠记忆编号选择。
- 范围与用户已确定的内容：2026-09-16 用户指定「右侧如同背包一样用同样动画弹出和收回，占据面积也跟背包一样，但是要接到屏幕最右边」。背包抽屉的既有实现见 `ColdSteelHUDWidget::UpdateInventoryLayout`／`ColdSteelInventoryTheme.cpp`。
- 阶段：游戏接入。关闭编辑器后完成 Editor Development 编译（`Result: Succeeded`；面板初版 17:06、按用户实测反馈修正两阶段交互后 17:13 两次落盘，模块 `Binaries/Win64/UnrealEditor-FPSGAME.dll`）；未运行游戏、未截图，视觉与手感由用户测试。首次尝试被运行中的编辑器拒绝（`Unable to build while Live Coding is active`）。
- 对照的现有面板、实际源码与规范版本：`ColdSteelWarehouseWidget`（抽屉外壳、分区、卡片与滚动）、`ColdSteelHUDWidget.cpp`（`DrawerProgress` 动画）、冷钢 UI 正式规则 2.16、`Source/FPSGAME/UI/ColdSteelUIStyle.h`。

## 信息结构与布局

| 栏目 | 内容与优先级 | 宽屏位置 | 窄窗／矮窗位置 | 固定或滚动 | 显示条件 |
| --- | --- | --- | --- | --- | --- |
| 顶栏 | 「自由建造」标题、当前材料／构件与计数 | 抽屉第 1 行 | 同宽屏，字号不变 | 固定 36px | 建造模式开启 |
| 状态区 | 材料／形状／吸附摘要、放置反馈、结构状态 | 顶栏下 | 同上 | 固定，自动换行 | 同上 |
| 分类页签 | 材质、构件两分类 | 状态区下 | 同上 | 固定 36px | 同上 |
| 卡片列表 | 材质卡：名称＋ID；构件卡：名称＋`格数 × 20 cm` 尺寸 | 页签下 | 同上 | 独立滚动，滚动条 6px | 同上 |
| 页脚 | 1/2 材料、3-9 构件、滚轮、R、F、左右键、Ctrl+Z、B/Esc | 抽屉底部 | 矮窗（高<650px）压缩为四行简写 | 固定 | 同上 |

## 主题与资源

| 元素 | 复用主题／组件 | 字体角色与字号档 | 资源来源及加载位置 |
| --- | --- | --- | --- |
| 抽屉外壳 | `UBackgroundBlur` 强度 9／半径 21＋`GlassTint` 248/255、圆角 10px、1px 细边 | 不适用 | 工程字体目录与 `ColdSteelUIStyle` |
| 顶栏 | `HeaderTint` | 标题 20px Medium，计数 12px 数字 | 同上 |
| 状态区 | `Success`／`Warning` 语义色 | 反馈 14px，结构状态 12px | 同上 |
| 同级按钮 | `ColdSteelUI::ButtonStyle`，两页签等宽、间距 4px | 14px Medium（选中） | 同上 |
| 卡片 | 未选 `StatusCard`＋1px 细边；选中 `ButtonHover`＋2px 银白边，圆角 8px | 名称 14px，尺寸 12px 数字 | 数据来自 `DA_VoxelBuildPalette` |

抽屉几何：贴屏幕最右（右侧外沿 0px），上下边距 12px，宽度 = 视口 48%，限制在 720–1040px，并服从视口可用宽度。0.25 秒常量插值展开／收回（`FInterpConstantTo(..., 4.0f)`），与背包抽屉同一节奏。

## 数据与动作

| 字段或操作 | 模型／业务入口 | 来源范围与过滤 | 单位／排序／公式 | 更新触发 | 确认、扣除与保存 |
| --- | --- | --- | --- | --- | --- |
| 材质卡 | `UVoxelBuildPalette::Materials` | 当前调色板全部有效 ID | 宽松显示 `DisplayName`，右侧显示稳定 ID | 调色板载入时推送一次 | 点击／1／2 调用 `SelectMaterial`，无资源消耗 |
| 构件卡 | `UVoxelBuildPalette::Components` | 当前调色板全部有效 ID | `Footprint × 20 cm` | 同上 | 点击／3-9 调用 `SelectComponent`，无资源消耗 |
| 已建造格数 | `AVoxelBuildWorld::BlockCount` | 本地世界体素 | 格 | 每帧 | 只读 |
| 构件数量 | `AVoxelBuildWorld::PrefabCount` | 本地世界构件 | 件 | 放置／拆除后 | 随世界存档写入 |
| 放置反馈 | `Feedback`／`TargetMessage`／`PrefabMessage`＋`StructureStatus` | 建造组件与建筑世界 | 文本 | 每帧 | 只读 |

面板只调用 `UVoxelBuildComponent::SelectMaterial／SelectComponent` 与既有世界接口，不自行扣除材料、不写存档。构件的放置、旋转、拆除与持久化见 [构件放置](../../Building/voxel-prefab-20260916.md)。

## 状态与输入

| 状态／触发 | 显示、隐藏或禁用 | 原因文案／反馈 | 选择、焦点、滚动与确认行为 |
| --- | --- | --- | --- |
| 未进入建造 | 抽屉收起（Collapsed，不参与命中与 Tick） | 无 | 保持游戏输入 |
| 按 B 打开面板 | 抽屉 0.25 秒滑入，光标显示，移动／视角输入被忽略（`FInputModeUIOnly`） | 「面板已接管光标 · 游戏操作暂停」 | 鼠标与键盘归面板；视角不再跟随鼠标 |
| 面板中选中材质／构件 | 抽屉自动滑出，光标隐藏，恢复 `FInputModeGameOnly` | 顶栏显示当前项 | 卡片点击，或 1/2／3-9／0；选中即进入建造 |
| 建造中按 B | 抽屉滑入，重新接管光标 | 「面板已接管光标 · 游戏操作暂停」 | 回到面板换材料／构件 |
| 面板中再按 B | 收起抽屉并**退出建造**，输入全部归还游戏 | 无 | 与打开面板前的纯游戏状态一致 |
| Esc | 退一层：面板 → 建造 → 退出建造 | 无 | 与 B 的差别是 Esc 在面板里只回到建造，不直接退出 |
| 未命中可放置表面 | 卡片仍可选 | 「未命中可放置表面 · 瞄准 6 米内的地面或结构」 | 预览隐藏 |
| 可放置／受阻 | 卡片与预览同步 | 「可放置 …」／「该位置已有构件／体素方块」 | 绿色可提交、红色只提示 |
| 选中材质／构件 | 卡片高亮，另一分类未选中的卡片取消高亮 | 顶栏显示当前项 | 1／2 回到材质，0 清除构件选择 |
| 分类切换 | 页签样式切换，列表重建 | 空列表显示「暂无构件 · 请在调色板 Components 中添加」 | 重建只在内容或分类变化时发生，选择变化只改画刷 |

- 键鼠入口：面板阶段光标归属面板（点击卡片、页签；键盘 1/2／3-9／0 等效），建造阶段光标归还游戏（准星瞄准、左右键放置／拆除）。两阶段由 `SelectMaterial`／`SelectComponent` 自动切换，不需要额外按键。
- Construct／Destruct 责任：`UVoxelBuildWidget` 自建 UMG 树并在 Tick 内做布局、动画与卡片刷新；`UVoxelBuildComponent` 拥有建造状态并推送数据；关闭时不重建控件。

## 文件范围与交付

- 本次修改文件：`Source/FPSGAME/Building/VoxelBuildWidget.h/.cpp`（抽屉与卡片）、`VoxelBuildComponent.h/.cpp`（抽屉开关、选择、构件放置分支）、`VoxelBuildPrefabActor.h/.cpp`（构件单体）、`VoxelBuildWorld.h/.cpp`／`VoxelBuildWorldPrefab.cpp`／`VoxelBuildWorldSave.cpp`／`VoxelBuildPersistence.h/.cpp`／`VoxelBuildTypes.h`（构件记录与存档 v4）。
- 复用资源：`DA_VoxelBuildPalette` 中已存在的材料与构件条目、`M_Voxel_PlacementPreview` 预览材质、冷钢主题与工程字体。
- 新增资源：无（构件网格沿用罗马柱案例已导入的资产）。
- 确认退役的文件、保留替代物、trash 目录及归档清单：无。
- 需要的必要构建：Editor Development（原生模块），已完成。命令为 `Build.bat FPSGAMEEditor Win64 Development -Project="D:\FPS3D\FPSGAME\FPSGAME.uproject" -WaitMutex`；新增类型与成员无法热补丁，需重启编辑器加载新模块。
- 用户明确要求的预览／检查／测试及交付文件：未要求，由用户测试。
- Git 发布：体素建造系统与并行会话归属交叠，按 §15.7 本轮不提交这些源码；纯本会话资产与工具按根目录 WORKFLOW 第 8 节单独推送。

## 其他构造子菜单（2026-09-16 第二版）

### 目标与交付阶段

- 名称、入口、解决的操作需求：建造抽屉「材质」分类下，每张材质卡右侧新增「其他构造」按钮；展开后在该材质下方列出这栏材质可以使用的其余构造（体素形状与同材质构件）。玩家不用记住滚轮顺序，也不用先去「构件」分类找同类部件。
- 范围与用户已确定的内容：2026-09-16 用户指定——① 材质行右侧加展开按钮；② 子菜单显示现有滚轮切换的其余体素构造（1 平方米地块、1 平方米墙面）；③ 新增 1×5 体素的水平／垂直直线构造；④ 同材质构件归入该材质的「其他构造」（罗马柱 → 大理石）；⑤ 原「构件」分类改名为「其他」。
- 阶段：游戏接入。关闭编辑器后 `Tools/Build/Build-Editor.ps1` 完成两次 Editor Development 全量编译（19:32 面板与形状、19:34 抽屉按键守卫；均 `Result: Succeeded`，只剩未改动的旧警告；新增 UPROPERTY 不能用 Live Coding 热补丁），随后另起 `UnrealEditor-Cmd` 进程写调色板归属（`save_packages=True`，同进程读回 `roman_column → marble`、`baluster_small → stone`；文件 19:33:26、4969 B，名字表新增 `Material` 条目）。未运行游戏、未截图，视觉与手感由用户测试。
- 对照的现有面板、实际源码与规范版本：本文件上一版（材质／构件两分类抽屉）、`ColdSteelWarehouseWidget` 的下拉与分区、冷钢 UI 正式规则 2.16、`Source/FPSGAME/UI/ColdSteelUIStyle.h`。

### 信息结构与布局

| 栏目 | 内容与优先级 | 宽屏位置 | 窄窗／矮窗位置 | 固定或滚动 | 显示条件 |
| --- | --- | --- | --- | --- | --- |
| 材质卡行 | 名称＋ID（点击＝选材质，沿用上次形状） | 分类页签下第 N 行 | 同宽屏 | 独立滚动 | 材质分类 |
| 其他构造按钮 | 「其他构造」，位于材质卡行右端，展开态用选中样式 | 同行右端，宽 96px、高 26px | 同宽屏 | 随材质行 | 材质分类；每张材质卡各一个 |
| 子菜单条目 | 该材质的体素构造（单格／1 平方米地块／1 平方米墙面／1×5 水平直线／1×5 垂直直线）＋同材质构件 | 材质行下方缩进 14px | 同宽屏 | 与列表同一滚动 | 该材质已展开 |
| 其他分类 | 全部放置构件（原「构件」分类，改名） | 分类页签下 | 同宽屏 | 独立滚动 | 切到「其他」 |

- 子菜单不新建浮层：条目直接插在材质行下方、随列表滚动，展开只改变列表内容高度。
- 展开态按材质独立记忆；选择任意条目后抽屉正常收起，重新打开仍保持展开。
- 空列表：材质分类「暂无可用材质」，其他分类「暂无其他构造 · 请在调色板 Components 中添加」。

### 主题与资源

| 元素 | 复用主题／组件 | 字体角色与字号档 | 资源来源及加载位置 |
| --- | --- | --- | --- |
| 材质卡行 | `StatusCard`＋1px 细边，选中 `ButtonHover`＋2px 银白边，圆角 8px | 名称 14px，ID／数值 12px 数字 | `ColdSteelUIStyle` |
| 其他构造按钮 | `ColdSteelUI::ButtonStyle`；展开态与分类页签同一「选中」样式 | 12px Medium | 同上 |
| 子菜单条目 | `Content` 底＋1px 细边，圆角 6px；选中同上 2px 银白边 | 名称 14px，尺寸 12px 数字 | 同上 |
| 浮窗 | 与上一版同一装备栏浮窗卡片 | 标题 16px，行 14px | 同上 |

### 数据与动作

| 字段或操作 | 模型／业务入口 | 来源范围与过滤 | 单位／排序／公式 | 更新触发 | 确认、扣除与保存 |
| --- | --- | --- | --- | --- | --- |
| 体素构造条目 | `UVoxelBuildComponent` 的形状表（单格／地块／墙面／1×5 水平／1×5 垂直） | 全部 5 种，每种材质都可用 | 20 cm 格：1×1×1、5×5×1、5×1×5、5×1×1、1×1×5 | 面板推送内容时一次 | 点击调用 `SelectShape(Material,Shape)`，无资源消耗 |
| 同材质构件 | `UVoxelBuildPalette::Components[].Material`（新字段） | 归属等于该材质行 ID 的构件 | 构件名＋占格尺寸 | 同上 | 点击调用 `SelectComponent`，无资源消耗 |
| 其他分类条目 | `UVoxelBuildPalette::Components` | 当前调色板全部有效构件（含未归类） | 同上 | 同上 | 同上 |
| 材质归属 | `FVoxelBuildPrefab::Material` | 调色板资产，作者脚本 `SourceAssets/RomanColumn20260915/set_prefab_panel_material.py` 写入 | 材质稳定 ID；空＝只在「其他」分类 | 进世界读一次 | 只读；改归属不需要动存档 |

形状与构件只写入建造状态（`SelectedMaterial`／`SelectedComponent`／`Brush`），扣除、放置与存档仍走 `AVoxelBuildWorld` 既有入口。

### 状态与输入

| 状态／触发 | 显示、隐藏或禁用 | 原因文案／反馈 | 选择、焦点、滚动与确认行为 |
| --- | --- | --- | --- |
| 未展开 | 子菜单条目不参与命中与编号 | 无 | 「其他构造」按钮为常态样式 |
| 已展开 | 条目插在该材质行下方并进入数字键编号 | 无 | 按钮切到选中样式，再点收起 |
| 选中体素构造 | 该材质行与其形状条目同时高亮 | 状态区显示「材质 · 形状 · 尺寸」 | 走 `SelectShape`，抽屉收起并回到建造 |
| 选中构件 | 构件条目高亮，材质行取消构件高亮 | 状态区显示构件名与占格 | 走 `SelectComponent` |
| 面板中 1-9 | 按当前可见行顺序选择（含展开出的子条目） | 无 | 与鼠标点击同一条 `Pick` 路径 |

- 滚轮仍按原顺序循环 5 种形状：单格 → 1 平方米地块 → 1 平方米墙面 → 1×5 水平直线 → 1×5 垂直直线；`R` 对墙面与水平直线交换 X／Y。
- 展开按钮与材质选择按钮同行但互为兄弟控件，点展开不会顺带切换材质。
- Construct／Destruct 责任与上一版一致：`UVoxelBuildWidget` 只重建列表与样式，建造状态与存档由 `UVoxelBuildComponent`／`AVoxelBuildWorld` 持有。

### 文件范围与交付

- 本次修改文件：`Source/FPSGAME/Building/VoxelBuildPalette.h`（构件归属字段）、`VoxelBuildComponent.h/.cpp`（形状表、`SelectShape`、面板内容分组）、`VoxelBuildWidget.h/.cpp`（其他构造子菜单、其他分类改名）、`SourceAssets/RomanColumn20260915/set_prefab_panel_material.py`（写入归属）。
- 复用资源：`DA_VoxelBuildPalette` 现有材质与构件条目、罗马柱案例资产、冷钢主题与工程字体。
- 新增资源：无。
- 确认退役的文件、保留替代物、trash 目录及归档清单：无。
- 需要的必要构建：新增 `UPROPERTY` 与 USTRUCT 字段不能热补丁，关闭编辑器后执行 `Tools/Build/Build-Editor.ps1`（FPSGAMEEditor Win64 Development）；构建完成后另起 `UnrealEditor-Cmd` 进程写入调色板归属。
- 用户明确要求的预览／检查／测试及交付文件：未要求，由用户测试。

## 材质行图标与页脚（2026-09-16 第六版）

- 材质行左侧补上 **28 px 缩略图**（用该材质自己的体素方块网格，走 `UVoxelBuildIcons` 的同一套固定视角/归一化取景），与「其他构造」卡片保持一致；缓存键 `shape:<材质>:-1`（单格）。
- 页脚（宽/矮两套）改写为新语义：`左键放置（消耗体素块）/ 右键拆除（方块进背包）· Ctrl+Z 拆掉最近一批建造 · Z 拾取周围掉落（含体素块、装备）`。

## 结构预警展示（2026-09-16 第五版）

用户要求：把"最弱接缝 ≥ 0.85 预警"实际做出来，并确定展示方式。结论是**两处、两种粒度**——面板里常驻可读，画面里越线播报一次；不新增常驻 HUD 控件。

| 位置 | 形态 | 内容 | 触发 |
| --- | --- | --- | --- |
| 抽屉状态区（面板打开时） | 状态行下方一条**预警行**，默认 `Collapsed` | 警告（≥85%，`Warning` 琥珀色）：`结构预警 · 抗剪 92% · 格(39,-30,10) · 加厚或补支撑`；超限（≥100%，`Danger` 红）：`结构超限 · 正在断裂 · …` | 每次推送面板内容时按 `AVoxelBuildWorld::WeakestJointRatio()` 更新 |
| 提示栏（建造中也能看到，屏幕上方） | 复用升级提示队列 `PostNotice` | `结构预警` / `结构超限` + 接缝摘要与建议，时长 3.2 s | **边沿触发**：跨过 85% 播报一次、跨过 100% 再播报一次；回落到 80% 以下重新武装，稳定在阈值上不会刷屏 |

数据链路：`VoxelStress::Solve` → `FVoxelStressResult::WorstBond` → `FVoxelBuildRuntime::WorstBond` → `AVoxelBuildWorld::WeakestJointRatio()/WeakestJointSummary()` → 面板预警行与提示栏。

为什么不用常驻 HUD 大字/图标：现有玩法 HUD 顶部已有血量与提示栏位置，再加一条常驻警示会和"提示栏=临时播报"的定位冲突；面板负责精确读数（应力、kPa、格坐标），提示栏负责越线提醒，玩家按 B 回面板即可查详情。

## 其他构造卡片网格（2026-09-16 第四版）

### 目标与交付阶段

- 用户要求：把「体素旁的其他构造」条目（材质行展开出来的形状与同材质构件）做成**同样大小的卡片**，**等距横向排列**、一行满了换行；每张卡片含**该组件的图片和名称**，图片**取相同视角、相同的缩放大小**。
- 阶段：游戏接入。实现为 `UVoxelBuildIcons`（运行时缩略图）＋ `UVoxelBuildWidget` 的 `UWrapBox` 卡片网格；未运行游戏、未截图，视觉由用户测试。
- 对照：工作台预览的双通道捕获＋`M_WeaponPreviewResolved` 合成（`Docs/UI/gunsmith-preview-quality-20260913.md`、技能参考 preview-rendering）、冷钢 UI 正式规则第 3/5 节（卡片 8px 圆角、1px 细边、选中 2px 银白边、同距排列）。

### 信息结构与布局

| 栏目 | 内容与优先级 | 宽屏位置 | 窄窗／矮窗位置 | 固定或滚动 | 显示条件 |
| --- | --- | --- | --- | --- | --- |
| 材质行 | 名称＋ID＋「其他构造」按钮（第二版保持不变） | 列表第 N 行 | 同宽屏 | 独立滚动 | 材质分类 |
| 其他构造网格 | 该材质的 5 个体素构造 ＋ 同材质构件，每个一张卡 | 材质行下方，缩进 14px | 同宽屏，按可用宽度自动换行 | 与列表同一滚动 | 该材质已展开 |
| 其他分类网格 | 全部放置构件（原「其他」分类列表） | 页签下 | 同上 | 独立滚动 | 切到「其他」 |

卡片规格（全部 DPI 反算，`PixelScale` 统一缩放）：卡片 **116 × 150 px**，图片 **104 × 104 px**，卡与卡之间 **8 px**（横竖同距），名称 12px 居中、允许两行；卡片底色 `Content`、圆角 8px、1px 细边；选中 `ButtonHover`＋2px 银白边；悬停同色系提亮。图片区在卡片内水平居中，名称在图片下方。

### 主题与资源

| 元素 | 复用主题／组件 | 字体角色与字号档 | 资源来源及加载位置 |
| --- | --- | --- | --- |
| 卡片外框 | `ColdSteelUI::Content`＋`CardRadius`；选中 `ButtonHover`＋`Accent` | 名称 12px | `ColdSteelUIStyle` |
| 卡片图标 | 工作台同一套：`FPreviewScene`＋`T_StudioEnvironment`＋正交捕获＋`M_WeaponPreviewResolved` 合成（`PreviewTexture` RGB→自发光、`PreviewCoverage` A→OneMinus→不透明度） | 不适用 | `/Game/UI/GunsmithWorkbench/*`（复用，不新增资产） |
| 体素形状网格 | 体素方块网格（材质条目 `ExampleMesh`，缺省按 wood/stone 回落到 `SM_Voxel20_Wood`／`SM_Voxel20_Stone`），材质取该材质行的 `Surface` | 不适用 | `/Game/Building/Voxels/Rounded/*` |
| 构件网格 | 构件条目的 `Mesh`／`Surface`／`PivotOffsetCm` | 不适用 | 调色板条目 |

### 图片取景（"相同视角、相同缩放大小"）

| 项 | 规则 |
| --- | --- |
| 视角 | 唯一固定旋转 `FRotator(-18, -35, 0)`：同一俯角、同一偏航、正交投影（无透视近大远小），所有卡片一致 |
| 缩放 | 按对象**包围盒最长边**归一化：`OrthoWidth = MaxDim / 0.78`，即每个构造都占画面 78%，卡片里看起来一样大；不按真实米数等比（20 cm 方块与 2.6 m 罗马柱同尺寸呈现） |
| 构图 | 先算所有可见网格的世界包围盒，再整体平移把中心对到摄像机光轴中心；摄像机距离 `300 + 2×MaxDim`，近远裁剪面按 `±1.4×MaxDim` 固定，避免自动平面裁切 |
| 分辨率 | 256 × 256（RGBA16f 颜色 ＋ RGBA8 覆盖率），满足 104px 图在 ~200% DPI 下的清晰度 |

### 数据与动作

| 字段或操作 | 模型／业务入口 | 来源范围与过滤 | 单位／排序／公式 | 更新触发 | 确认、扣除与保存 |
| --- | --- | --- | --- | --- | --- |
| 形状缩略图 | `UVoxelBuildIcons::KeyForShape(材质, 形状序号)` | 每材质 5 种形状，`IconCells` 由 `BrushShapes` 的表按 20 cm 格展开 | 键＝`shape:<材质>:<序号>` | 重建卡片时请求一次，缓存命中直接贴图 | 只读；不进存档 |
| 构件缩略图 | `UVoxelBuildIcons::KeyForPiece(构件 ID)` | 调色板 `Components` 条目 | 键＝`piece:<ID>` | 同上 | 只读 |
| 选取 / 编号 | 与第二版一致（`Pick`／`SelectShape`／`SelectComponent`，1-9 按可见卡片顺序） | 卡片顺序＝形状在前、构件在后 | — | 点击、键盘 | 走既有建造入口 |
| 缓存 | `UVoxelBuildIcons` LRU，最多 16 个键；淘汰时释放两个 RT 与 MID | 每帧只处理一个捕获作业 | — | 请求时入队 | 子系统 Deinitialize 释放全部 RT |

### 状态与输入

| 状态／触发 | 显示、隐藏或禁用 | 原因文案／反馈 | 选择、焦点、滚动与确认行为 |
| --- | --- | --- | --- |
| 图标未就绪 | 卡片先显示名称，图片区留空 | 无（后台排队，每帧 1 个） | 仍可点击、可编号；就绪后由 Tick 贴图，不重建卡片、不打断滚动 |
| 图标失败（网格缺失） | 图片区保持空，其余不变 | 记 `LogTemp:Warning VoxelBuildIcon: failed key=...`，同一键不再重试 | 名称与交互不受影响 |
| 选中／悬停 | 与第二版一致（2px 银白边／提亮） | 状态区显示当前项 | 悬停出浮窗（浮窗跟随鼠标、按视口限位） |
| DPI／视口变化 | 卡片尺寸、图片尺寸与 8px 间距一起按 `PixelScale` 重算 | 无 | 重建仅改尺寸，不重建卡片内容 |

### 文件范围与交付

- 本次新增：`Source/FPSGAME/Building/VoxelBuildIcons.h/.cpp`（缩略图子系统）。修改：`VoxelBuildWidget.h/.cpp`（`UWrapBox` 卡片网格、图标贴图、DPI 重算）、`VoxelBuildComponent.cpp`（形状/构件/材质的图标数据源）。
- 复用资源：`/Game/UI/GunsmithWorkbench`（`M_WeaponPreviewResolved`、`T_StudioEnvironment`）、`/Game/Building/Voxels/Rounded/*`、调色板条目的构件网格；**无新增资产**。
- 确认退役：无（上一版的行式子菜单组件 `AddCardRow` 被卡片网格取代，直接删除，未留死代码）。
- 必要构建：Editor Development（新增 UCLASS 子系统与控件结构，不能热补丁）。
- 用户明确要求的预览／检查／测试及交付文件：未要求，由用户测试。

## 状态区最弱接缝读数（2026-09-16 第三版）

用户报告"垂直建造卡在 1 m"后，面板的结构状态行增加一行来自解算结果的读数（见 [垂直建造卡 1 m 排查](../../Building/voxel-vertical-build-diagnosis-20260916.md)）：

| 项 | 内容 |
| --- | --- |
| 文案 | `最弱接缝 抗剪 84/80 kPa · 105% · 格(39,-30,10)`；受压／受拉·弯按同一格式换词 |
| 数据来源 | `FVoxelStressResult::WorstBond` → `FVoxelBuildRuntime::WorstBond`（上一次发布解算的最弱接缝）；回退时显示 `FailureBond`（那一次失败放置的最弱接缝） |
| 位置 | 既有的结构状态行（`AVoxelBuildWorld::StructureStatus()` 返回值），建造中与面板内都可见，沿用 12px 次要文字，不新增控件 |
| 更新触发 | 每次承重解算发布、以及每次放置失败回退 |
| 边界 | 只读；接缝坐标用于玩家判断该加固哪一段。旧建筑保护/未收敛等既有状态文案优先保持不变 |
