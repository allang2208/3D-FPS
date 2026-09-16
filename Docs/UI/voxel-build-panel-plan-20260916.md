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
