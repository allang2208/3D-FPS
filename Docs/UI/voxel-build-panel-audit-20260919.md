# 建造面板静态审计（2026-09-19）

范围：对「自由建造」抽屉做一次静态审计，对照个人技能与工程镜像一致的冷钢 UI 规则、建造面板既有规划与实际实现。**初查未启动游戏、未编译、未截图**；同日用户拍板修复并已实施（见文末「修复实施」），未运行游戏，视觉与手感交由用户测试。

## 对照来源

| 类别 | 文件 |
| --- | --- |
| 技能 | `skills/ue5-ui-umg-slate/SKILL.md`（UI Stage Contract、生命周期、浮窗限位）与 `references/fpsgame-panels.md`（2026-09-16/17 建造抽屉各节） |
| 正式规则 | `Docs/UI/ui-cold-steel-design-system.md` 2.17（右抽屉规格，含让位与压暗底） |
| 规划 | `Docs/UI/voxel-build-panel-plan-20260916.md`、`Docs/UI/voxel-build-icon-lifetime-plan-20260917.md` |
| 实现 | `Source/FPSGAME/Building/VoxelBuildWidget.h/.cpp`、`VoxelBuildIcons.h/.cpp`、`VoxelBuildComponent.cpp`（抽屉、输入、内容推送段） |

## 总体结论

主体按规则落地：主题只取 `ColdSteelUIStyle`、卡片/字号/滚动条全部按 `PixelScale` 反算、展开态跨开合记忆、数字键与可见行同序的主路径、图标「正在显示不回收」与失效重贴（09-17 两项修复）均已在代码中。发现 **3 个中影响项、3 个低影响项**。

## 1.（中）DPI／视口变化会把材质行重排成大卡片

- `RefreshLayout` 对 `Cards` 中**所有**条目统一套网格卡尺寸：`VoxelBuildWidget.cpp:624-628` 把 `Card.Box` 设为 116×150、`Card.IconBox` 设为 104²。
- 但材质行登记进 `Cards` 的这两个盒子不是网格卡的：行高盒 `(CardHeight-8)=36px`、缩略图盒 `28px`（`VoxelBuildWidget.cpp:484-501`、登记在 `:522`；网格卡登记在 `:459`）。
- 触发条件：`RefreshLayout` 只在视口或 `PixelScale` 变化时重跑（`:611`），首次布局时 `Cards` 为空所以初始正常；**之后任何窗口尺寸/DPI 变化**都会把每张材质行撑成 150px 高的大卡片、28px 缩略图变 104px。
- 建议：`FCard` 增加显式「网格卡」标志（`bChild` 不能当判据——「其他」分类的网格卡也是 `bChild=false`），刷新时只对网格卡套网格尺寸，材质行按 36/28 重算。

## 2.（中）数字键兜底落到旧调色板顺序，可能选中不可见条目

- 抽屉键盘路径：可见卡命中走 `Pick`，未命中却继续落到 `HandleDrawerKey → HandlePanelKey`（`VoxelBuildWidget.cpp:333`、`VoxelBuildComponent.cpp:282-297`），后者按**调色板顺序**（材质在前、构件在后）选择。
- 例：材质分类只显示 3 张材质行，按 `4` → 可见卡未命中 → 兜底命中「构件 #1」→ `SelectComponentByIndex` 选中一个当前分类根本没显示的门/柱并关抽屉开建。
- 与 SKILL「可见行顺序就是数字键顺序」和页脚文案「1-9 选当前分类第 N 项」矛盾；这是建造态快捷键（旧行为）与抽屉可见行编号两套顺序的残留冲突。
- 建议：抽屉打开时数字键只认可见卡，未命中即忽略（不落到调色板顺序）。

## 3.（中）抽屉规格缺压暗底／玻璃淡入，且未接 HUD 让位

- 用户要求「和背包同样弹出收回」（`voxel-build-panel-plan-20260916.md`），SKILL／正式规则 2.17 的现行右抽屉规格为：同一条 4.0/s 进度驱动**滑出距离＋全屏 40% 压暗底＋玻璃淡入**，抽屉出现期间右侧栏目入口、世界时钟、右下武器详情**同步收起**。
- 建造抽屉目前只做了位移：`VoxelBuildWidget.cpp:678-680` 仅改 `RenderTranslation`，没有压暗层、没有随进度的透明度（对照背包 `ColdSteelHUDWidget.cpp:195-203` 同时驱动 Backdrop/Blur 透明度；开发面板 `DevelopmentPanelWidget.cpp:225-250` 有 `DrawerBackdrop`）。
- 让位：建造组件打开抽屉时没有调用 `HUD->SetExternalDrawerOpen(true)`（组件 `SetPanelOpen` `VoxelBuildComponent.cpp:239-268` 无此调用；对照 `DevelopmentPanelWidget.cpp:241/523-526`）。HUD 消费方是同一标志（`ColdSteelHUDWidget.cpp:210/1134`、`ColdSteelPanelNavigation.cpp:131`）。实际表现是右侧入口列/世界时钟/右下武器详情不参与让位、被抽屉玻璃压住，而不是像背包那样收起。
- 建议：按开发面板同一模式补 `SetExternalDrawerOpen`（打开置位、收回动画播完复位、`NativeDestruct`/`EndPlay` 直清），压暗底与玻璃淡入按背包参数补。

## 4.（低）缩略图尝试计数把成功也计入；放弃分支逐帧告警

- `VoxelBuildIcons.cpp:244` 每次构建后都 `GIconAttempts++`（注释写的是「after a failed build」）；同一键累计 3 次（含成功）后 `Request` 永久拒绝（`:52-57`）。键被 LRU 回收后需要重建时会因计数耗尽而回不来（周期内切分类反复展开可触发）。
- 放弃分支每被调用一次就 `UE_LOG(Warning)`，而控件每帧对无图卡重新 `Request`（`VoxelBuildWidget.cpp:385-386`）→ 抽屉打开期间逐帧刷同一条警告日志。
- 建议：计数只在失败时递增、成功清零；放弃日志按键只打一次。

## 5.（低）清理项

- `VoxelBuildIcons.h:67` 的 `Failed` 集合只有 `Reset` 没有写入，是留着名字的死字段（弃用 blacklist 的残留）。
- `Labels` 只在写入不清理（`VoxelBuildWidget.cpp:73`、刷新在 `:629`）：每次 `RebuildCards` 新增十几条弱引用，旧条目失效后仍留在数组里逐帧参与字体刷新循环。

## 6.（低）三处小瑕疵

- 子菜单卡选中态圆角 8→6px 跳变：卡片底色/悬停用 `CardRadius`（`:434-446`），选中在 `RefreshSelection` 里对 `bChild` 用 `ButtonRadius`（`:591-594`）。另外规划写的子菜单 6px 圆角其实从未在常态出现。
- 浮窗关闭按钮实际不可点：`UpdateTooltipPlacement` 每帧把浮窗钉在光标外 10px（`:241-259`），`HideTooltip` 的「指针在浮窗内则保持」分支（`:221-237`）永远不会命中——光标永远在卡外，一靠近就跟着走或先触发 Unhover 收掉。关浮窗只能靠移出卡片/切分类/关抽屉。
- 页签字重不一致：`Tab()` 把「是否构件分类」直接传给了 `Text` 的 Medium 参数（`:81`），结果「其他」页签恒为 Medium、「材质」页签恒为 Regular，不随选中态变化（规划为「14px Medium（选中）」）。

## 未做（初查阶段）

- 未运行游戏、未跑构建、未截图；所有结论来自读码与规则对照。修复范围与优先级待用户确认后另行实施。

## 修复实施（2026-09-19，用户拍板后）

### 1. DPI／视口变化不再重排材质行

- `FCard` 增 `bGridCard`：网格卡（其他构造卡片）为 true，材质行为 false（`VoxelBuildWidget.h/.cpp` 两处登记点）。
- `RefreshLayout` 按标志分流：网格卡保留 116×150／104² 重算；材质行只重算行高 36px 与 28px 缩略图（常量提为 `MaterialThumbPixels`）。

### 2. 数字键只认可见行（双端收口）

- 控件侧：`NativeOnKeyDown` 数字键未命中可见卡即吞掉，不再走 `HandleDrawerKey → HandlePanelKey` 的调色板顺序（`VoxelBuildWidget.cpp`）。
- 组件侧：`HandleInput` 在 `bPanelOpen` 时数字键由控件独占；组件只处理面板收起（建造态）的调色板顺序快捷键（`VoxelBuildComponent.cpp`）。

### 3. 抽屉规格补全：压暗底、玻璃淡入与 HUD 让位

- 新增全屏 40% 压暗底 `Backdrop`（ZOrder 0，`HitTestInvisible`——建造面板没有"点外部关闭"，不能吞掉回到瞄准后的点击），与 `Blur` 透明度一起由同一条 `DrawerProgress` 驱动（`NativeTick`）。
- 新增 `SetHudYielded` + `ResolveHUD`：打开时调 `HUD->SetExternalDrawerOpen(true)`，`NativeTick` 在收回动画播完（进度归零）时复位；`NativeDestruct` 与组件 `EndPlay` 各有一条直清路径，销毁流程不跑动画也不会漏解让位。

### 4. 缩略图计数与日志

- `VoxelBuildIcons`：失败计数只在失败时递增、成功后清零（旧实现成功也计数，回收重建 3 轮后永久拒绝）；新增 `GIconGaveUp` 集合，放弃只记一次日志，之后 `Request` 静默跳过。
- 清理 `Failed` 死成员；控件 `RebuildCards` 开始处 `Labels.RemoveAll` 清掉脱离控件树的旧条目。

### 5. 三处小瑕疵

- 子菜单卡选中态不再换圆角（统一与常态同半径，消除 8→6px 跳变）。
- 浮窗：显示后跟随 0.7s 自动钉住位置（`TooltipFollowSeconds`），钉住后指针离开浮窗与来源卡片才收起；`HideTooltip` 的"指针在浮窗内则保持"分支由此真正可达，关闭按钮可点。
- 页签：`Tab()` 不再把分类标志当 Medium 传入；`RefreshCategory` 按选中态设置两页签字重（选中 Medium / 未选中 Regular）。

### 验证状态

- 编译：`FPSGAME Win64 Development` **构建成功**（`Result: Succeeded`，`Saved/BuildEditor/buildpanel-fixes-retry-20260919.log`，含本轮三个改动文件）。首次构建曾因并行会话正在修改的 `VoxelBuildWorldPrefab.cpp`（构件焊接 WIP，缺 include，非本任务文件）中断，对方补完后同轮重试通过；未改动对方代码。
- 编辑器目标 `FPSGAMEEditor Win64 Development` 随后同样 `Result: Succeeded`（`Tools/Build/Build-Editor.ps1`），`UnrealEditor-FPSGAME.dll` 已更新，重启编辑器即生效。
- 未运行游戏、未截图；视觉、手感与让位时序由用户实测。