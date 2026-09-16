# 背包物品拖动转向（2026-09-16）

## 功能

- 按住左键拖动背包或仓库中的物品时，按 `F` 在 90° 两态之间切换摆放方向：竖放的剑变成横放，再按一次转回。放下后方向随该实例保存。
- 转向中的半透明拖动图、落点高亮框、交换回填框都跟随新朝向；转后放不下的落点仍显示原有红色拒绝与原因。
- 可转向物品拖动时，底部提示为 `拖动放置 / 交换物品 · F 调整摆放方向`。
- 装备栏 15 格与数字快捷栏不参与转向；占用格为正方形（1×1、2×2、3×3…）的物品不转向，`F` 无效果。

## 实现

- 数据：`FColdSteelItem::bRotated`（存档字段，旧存档缺省 false）。`Width`/`Height` 始终保存"应用朝向后的实际占用"，因此已有放置、交换、回填、整理、拆分、背包↔仓库转移逻辑无需逐处分支。
- 规则：`ColdSteelInventory::BaseFootprint` 是作者朝向，`Footprint` 按 `bRotated` 交换 X/Y，`ApplyOrientation` 统一写回朝向与 `Width`/`Height`。`Move`、`ColdSteelWarehouse::Transfer`、`ProposeMove`、`MoveItem`、`ProposeWarehouse`、`TransferWarehouse` 增加可选 `Orientation`（`-1` 保持当前值，默认参数不影响既有调用）。
- 拖动事务：`UColdSteelItemDrag::bRotated` 是本次拖动的待提交朝向（初始化为实例当前朝向）。转向时 `GrabNorm` 与 `GrabOffset` 转置，指针在物品矩形内的相对位置保持不变；松手时朝向与落点一起提交，取消拖动不改存档。
- 绘制：`ColdSteelDragVisual` 与背包／仓库面板都用 `FSlateDrawElement::MakeRotatedBox`（+90°，绕图像中心）绘制转向图；取景按转置后的矩形计算，画面不会超出占用格。
- 高亮：落点矩形读取面板的 `PreviewCells`（本次预览的待提交占用）；跨面板拖动（背包↔仓库）由拖动对象记录 `PreviewBoard`，按 F 后刷新对应面板的高亮与提单。

## 输入归属

- `F` 只在左键拖动进行中转向；非拖动状态仍是原来的"F 切换焦点区域"。按键重复被忽略，长按不会连续翻转。
- 键盘搬运（Space 携带）本轮不转向，保持原行为。

## 首版绘制缺陷与修正（2026-09-16）

用户反馈转向后贴图超出格子甚至不在格子里。两处原因都在 `MakeRotatedBox` 的用法上，已按格子原有取景方式对齐：

1. `MakeRotatedBox` 的旋转点参数是**元素本地像素**，不是 0–1 归一化值；首版按归一化传入 `(0.5, 0.5)`，等于绕"左上角内 0.5 像素"旋转，整块贴图被甩出格子。现在不传该参数，使用引擎默认值 `LocalSize * 0.5`（盒中心）。
2. 转向盒的**居中**沿用了未旋转的 `(H - Size.Y) / 2`，而旋转后的可见高度其实是 `Size.X`，竖长图标（剑）因此从卡片上下溢出。现在改为把盒中心放在格子图像区中心（`X + ImageX + ImageWidth/2`、`Y + H/2 + 名称偏移`）——这与原装备格／背包装备格未旋转实现的落点完全一致，旋转只改变可见范围，不改变取景基准。

未旋转的装备卡、背包格、快捷栏沿用同一公式，因此外观没有变化；转向只让"可见包围盒"（`Size.Y × Size.X`）落在同一张卡片内。

## 交付边界

## 拖动中转向的第二处缺陷与修正（2026-09-16，用户复现）

用户复现：枪械（5×2）在按住左键拖动中转成竖放（2×5）后放不进背包，转回横放仍显示红色拒绝、无法再移动位置。根因三处，均在本轮转向实现里：

1. `RefreshDragPreview` 带 `!IsVisible()` 提前返回（当时为跨面板安全加的守卫）。把 5 行高的枪械往 4 行背包里放时，指针必然要移到面板之外（锚点不可能落在网格内），此时 HUD 既有的"拖出面板即隐藏抽屉"会执行 `SetVisibility(Hidden)`；再按 F 时刷新被跳过，高亮停留在竖放那一次的红色拒绝上，此后不再重算锚点 —— 表现为"转回来还是红的、动不了"。
2. 旧实现每次转向都在**当前** `GrabNorm`／`GrabOffset` 上做转置加夹取，任何一次夹取都会永久污染锚点。改为拖动开始时记录 `BaseGrabOffset`／`BaseGrabNorm`，每次转向都从基准值推导且不做夹取，往返必然精确复原锚点。
3. `ColdSteelDragVisual::Configure` 每次转向都重建 `WidgetTree->RootWidget`，等于在拖动过程中重建活动 widget 树；改为只在首次创建。

修正内容：

- `RefreshDragPreview` 不再因面板不可见而跳过；指针不在本面板范围内时改为清空高亮（绝不留陈旧红框），指针回到面板内由正常 DragOver 重新计算。
- HUD 在拖放进行中接管 `F`（转发到 `InventoryDrag->SourceBoard->RotateDraggedItem`），因此抽屉被隐藏、焦点不在背包板时也能转向。
- 竖放需要 5 行而背包只有 4 行时给出明确原因（`这个方向需要 5 行，背包只有 4 行`），仓库 12 行仍可竖放，不再显示通用拒绝。
- 转向后同时刷新"预览面板"和持有拖动的面板的绘制，避免只有一边更新。

## 交付边界（补充）

## 落点锚点夹取（2026-09-16，按用户复现日志定位）

实测日志（`Saved/Logs/FPSGAME.log` 的 `INVDRAG` 行）显示转向状态本身完整往返：

```
begin ue_akm place=0 cell=8 stored=5x2 rotated=0 grab=(2,1)
F#1 rotate applied pending=1 flip=1 grab=(1,2) pendingCells=2x5 → reason=这个方向需要 5 行，背包只有 4 行
F#2 rotate applied pending=0 flip=0 grab=(2,1) pendingCells=5x2 → cell=14 valid=0 reason=物品超出背包边界，请向内移动
drop place=0 cell=10 pending=0 valid=0 result=0
```

即：朝向 0→1→0、占位 5x2→2x5→5x2、抓取偏移 (2,1)→(1,2)→(2,1) 全部精确复原，转向没有把实例弄坏。转回后仍然红是**落点规则**造成的：光标在第 16 列时锚点算到第 14 列，5 格宽的 AKM 顶出右边界 → `物品超出背包边界，请向内移动`。该规则在未转向时同样存在，只是"竖放→转回"的过程必然把光标推到边缘，于是看起来像转向导致放不下；松手那次锚点在第 10 列，几何可行，被拒是因为目标格被其他物品占着且自动腾挪失败。

修正：`PreviewItemDrag` 把锚点夹取到容器内（列 `0…18-W`、行 `0…Rows-H`），外层格不再直接报"超出边界"，而是把物品放在最靠外的可放位置；高亮框用的就是夹取后的落点，做到"看得见=放得下"。竖放枪械（需要 5 行而背包 4 行）仍给出明确原因，被占用的目标仍按原规则拒绝并给出原因。

定位期间曾加过一层 `INVDRAG` 追踪（拖动开始/按键归属/转向请求与应用/落点求解/松手结果/拖动结束），仅在这些事件时输出；问题确认后已随本次改动删除，需要时可按同样字段再挂一次。

- 未启动游戏测试，实际手感、落点与画面由用户测试。
- 转向只是摆放朝向，不改变物品数据、数值、图标构图与浮窗模型预览。
- 必要构建（最终）：`FPSGAMEEditor Win64 Development -ModuleWithSuffix=FPSGAME,9162230`（编辑器在运行时用后缀构建，避免占用旧模块）→ `Result: Succeeded`，产物 `Binaries/Win64/UnrealEditor-FPSGAME-9162230.dll`，日志 `Saved/BuildEditor/backpack-rotation-build-7.log`。更早的 `9162031`／`9162120`／`9162140` 与无后缀的 `Tools/Build/Build-Editor.ps1`（`build-20260916-210344.log`、`build-20260916-211657.log`）也各自 `Succeeded`；`.cpp` 改动另按 UBT 生成的编译命令逐文件复核（`Saved/BuildEditor/cl-check-*.log`，该方式不重跑 UHT，改动头部后必须走完整构建）。
- 期间 20:30:49 的并行全量构建曾失败：原因是本功能的四个编译错误（局部变量 `Cursor` 遮蔽 `UUserWidget::Cursor`、`auto` 多声明符、`Cells` 重复声明），已在数分钟内修复；随后 `9162031` 与 `9162105` 均 `Succeeded`。
