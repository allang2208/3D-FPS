# 建造抽屉缩略图存活与单格取景（2026-09-17）

交付范围：修复「木制材质的部分其他构造没有图片」，并把所有 1×1 体素块的预览图缩小 50%。属于 [建造面板抽屉规划](voxel-build-panel-plan-20260916.md) 第四／第六版缩略图规则的后续修订；用户已授权实现，按 2026-09-12 全局规则不追加检查、测试或验收。

## 1. 用户反馈与定位

反馈：① 建筑面板里木制材质的部分「其他构造」没有图片；② 所有 1×1 体素块的预览图缩小 50%。

定位过程（读源码与资产数据，不运行游戏）：

- 图标子系统 `UVoxelBuildIcons` 的 LRU 上限是 **16 个键**；抽屉一屏需要的键是「3 张材质行 \+ 每材质 5 个体素形状」＝ **18 个**（每材质展开一次即 3+5，三栏都展开就是 18）。
- 请求与贴图顺序：`RebuildCards` 按材质行 → 该材质形状的顺序入队，图标每帧只出 1 张；`RefreshIcons` 只对**还没有画刷**的图片调 `Find` 后贴图。
- 于是展开第三栏材质时，`Materials.Num()` 超过 16，淘汰循环挑走 `Uses` 最小的两个键——正是**最先出图的两张木制缩略图**（木制材质行与木制「单格」卡片）。这两张图当时的 `UImage` 已经贴好画刷，之后 `RefreshIcons` 因为"已有画刷"跳过重贴，而被淘汰的条目又释放了两个 RT，卡片就一直显示空图。
- 同一批键如果没有画刷就会被重新排队，所以表现为「部分条目没有图片」，而不是整栏失败；日志里没有 `VoxelBuildIcon: failed` 也符合这一点（不是出图失败）。

结论：不是网格缺失或捕获失败，而是**淘汰了正在显示的缩略图**，且控件缺少失效重贴路径。

## 2. 修改

### 2.1 让正在显示的缩略图不被回收

- `UVoxelBuildIcons::SetVisibleKeys(const TSet<FString>&)`：抽屉重建卡片时整体声明"当前显示的键"；淘汰循环跳过这些键，全部都在显示时宁可暂时超过 16 也不让卡片变空图。
- 控件侧 `UVoxelBuildWidget::RefreshIconPins()`：卡片重建后（`bIconPinsDirty`）把 `Cards` 的键集合交给子系统；集合相同则不重写，避免每帧重建哈希表。
- 不再显示的键（换分类、内容变化后的旧键）失去保护，仍按 LRU 在超过上限时回收。

### 2.2 贴图与缓存不同就重贴

- `FCard` 保存建卡时的 `FVoxelBuildIconRequest`，缓存被回收后可以按同一份参数重新排队。
- `RefreshIcons` 改为：`Find` 命中的图与当前画刷不是同一个材质实例就 `SetBrushFromMaterial` 重贴；没有图且没有画刷时重新 `Request`（失败键不会重复入队）。这样即使以后还有条目被回收，也会在一秒内自愈，而不会永久空白。

### 2.3 单格 1×1 体素块按一半大小绘制

- `VoxelBuildIcons.cpp` 新增 `SingleBlockFrameScale = 0.5`：`OrthoWidth = MaxDim / (IconFillFraction × 0.5)`，即单格请求的包围盒最长边只占画面 39% 而不是 78%，在同一张卡片里正好是原来的一半大小。
- 判定用请求自身的格子数（`Cells.Num() == 1`），因此**所有 1×1 体素块预览**一致生效：材质行左侧 28px 缩略图（键 `shape:<材质>:-1`）与「其他构造」里的「单格」卡片。其余形状（1 平方米地块／墙面、1×5 直线）与构件预览取景不变。

## 3. 保持不变

- 缩略图仍复用工作台的 `FPreviewScene` ＋ `T_StudioEnvironment` ＋ 正交捕获 ＋ `M_WeaponPreviewResolved` 双通道合成，固定视角 `FRotator(-18,-35,0)`，256×256 分辨率，每帧最多 1 个捕获作业。
- 卡片尺寸（116×150）、图片区（104×104）、间距（8px）、DPI 反算、悬停／选中样式、编号与点击行为不变。
- 缓存仍按需排队、失败不重试并记录 `VoxelBuildIcon: failed key=...`；`Deinitialize` 释放全部 RT 与 MID，并清空显示键集合。

## 4. 文件范围

- 修改：`Source/FPSGAME/Building/VoxelBuildIcons.h/.cpp`（显示键集合、淘汰保护、单格取景）、`Source/FPSGAME/Building/VoxelBuildWidget.h/.cpp`（请求留存、失效重贴、键集合声明）。
- 未改动调色板、构件网格、材质与存档；无新增资产。

## 5. 构建记录

- 本轮需要原生构建（改 `UCLASS` 子系统的成员与控件结构，不能热补丁）。
- `FPSGAME Win64 Development` → **Result: Succeeded**，产物 `Binaries/Win64/FPSGAME.exe`，日志 `Saved/BuildEditor/buildpanel-game-1.log`；该构建从新生成的 makefile 编译 200 个动作（含 `VoxelBuildIcons.cpp`、`VoxelBuildWidget.cpp`、`VoxelBuildComponent.cpp`）并链接成功。
- 编辑器目标当时**无法完成链接**，原因有二，都与本次改动无关：
  1. 用户编辑器正在运行并占用 `Binaries/Win64/UnrealEditor-FPSGAME.dll`，Windows 不允许覆盖已加载的模块；
  2. 首次编辑 `FPSGAMEEditor` 时链接报 `AFPSGAMECharacter::SuspendWeaponForMenu` 重复定义，来源是编辑器目标的**陈旧编译产物**（当前源码只有 `FPSGAMECharacter.cpp:1907` 一处定义，`Module.FPSGAME.2.cpp` 的包含列表里也没有该文件）。执行 `FPSGAMEEditor ... -Rebuild` 清掉旧产物后该重复定义消失。
- 重建后编辑器目标剩余的错误来自并行会话正在进行的 `FPSMagicPreview::DrawSegment` 签名改动（`FPSFireballProjectile.cpp:91`、`FPSIceSpikeVolley.cpp:179` 仍按 4 参数调用），不属于本次范围，未改动他人代码。
- 关闭编辑器后再跑 `Tools/Build/Build-Editor.ps1` 即可链接出可加载的 `UnrealEditor-FPSGAME.dll`。本轮未启动游戏、未截图、未做视觉或功能验收，由用户测试。
