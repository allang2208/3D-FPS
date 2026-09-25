# FPSGAME 背包输入、独立弹窗与拖放复查

适用于 FPSGAME 的 CommonUI/UMG 背包。先核对宿主 AGENTS 与当前 `Source/FPSGAME/UI`；以下路径相对项目根，历史 Godot 仅用于规则对照。

## 关闭与焦点

- `ColdSteelInventoryPopup` 通过 `AddToViewport` 成为独立根，其背景点击不会冒泡到 `ColdSteelHUDWidget`。背包与独立弹窗共用 `HandleInventoryOutsideClick`，避免只关菜单、背包仍打开。不要复制两份几何判断。
- 使用同一套屏幕绝对坐标与 `GetCachedGeometry().IsUnderLocation` 判断背包、仓库、详情与可见浮窗范围；点击受保护区域内继续原操作，区域外关闭并消费点击。
- 打开时根控件必须能接收外部点击，关闭时恢复原游戏输入。复查拖放结束后的根/背景可命中状态，不能只验证第一次打开；抽屉透明度不等于命中状态。
- 拖动中的外部移动和松手属于拖放，不按外部点击关闭。关闭或失焦取消拖放时恢复抽屉与源物品显示；随后松手不得再执行丢弃或快捷栏绑定。
- 当前用户约定：TAB 打开/关闭背包，已在属性页时 TAB 也关闭；Caps 进入/切换属性页。独立菜单的 `NativeOnPreviewKeyDown` 要转发快捷键，覆盖拆分输入框占焦点的情况；忽略按键重复，保留已有 Esc 语义。

## 跟手与数据合同

- 若自定义物品图标仍出现从别处飞入的动画，核对实际 Slate/UMG drag decorator 路径。当前实现使用 `ColdSteelDragVisual` 随指针定位；覆盖武器的所有占用格抓取，保留相对抓取偏移，检查 DPI 与滚动后的坐标转换。
- 源实例、预览目的地、释放事务和取消显示是不同状态。释放时按当前库存验证实例位置与提案，保存失败不提交；不要仅凭拖动开始时的预览允许交换。
- 画面正确之外，还需检查实例 ID、数量、弹药、改造数据、快捷栏解析、Generation 和重新读档。模型图标来自真实配件组合，不等于已完成库存事务迁移。
- 拖动中按 `F` 转向属于"待提交朝向"而非立即写盘：`UColdSteelItemDrag::bRotated` 初始化为实例当前朝向，转向时转置 `GrabNorm`／`GrabOffset` 保持指针在物品矩形内的相对位置，松手时朝向与落点一起提交，取消拖动不改存档。物品 `Width`／`Height` 必须始终等于应用朝向后的实际占用（`ColdSteelInventory::Footprint` 按 `bRotated` 交换 X／Y，`ApplyOrientation` 统一写回），这样放置、交换、回填、整理、拆分和仓库转移都不需要各自分支；只有占用格非正方形且目标是背包／仓库时才转向，装备栏、快捷栏与键盘搬运不转向。跨面板拖动由拖动对象记录预览面板，按 F 后刷新高亮。非拖动状态的 `F` 仍保留原有焦点切换语义。
- `FSlateDrawElement::MakeRotatedBox` 的旋转点是**元素本地像素**（默认 `LocalSize * 0.5`），传 `(0.5, 0.5)` 会变成绕左上角旋转并把贴图甩出格子；转向盒必须按"可见包围盒"（转置后的 `Size.Y × Size.X`）拟合并把**盒中心**放在格子的图像区中心（与未旋转实现的落点公式一致），否则竖长图标会从卡片上下溢出。首版转向正是因为这两点被用户看到贴图出格／不在格内。
- 拖出面板时 HUD 会把抽屉设成 `Hidden`（既有的"拖出即丢下"逻辑），所以**刷新落点预览不能因为面板不可见就提前返回**：否则按 F 转回原方向后高亮会停在旧的红色拒绝上，看起来"转回去还是红的、动不了"。正确做法是指针不在本面板内时清空高亮、回到面板内由正常 DragOver 重算；同时把转向键放在 HUD 层兜底（拖动进行中转发给发起面板），并在待提交朝向塞不进当前容器行数时给出明确原因（例如竖放步枪需要 5 行而背包只有 4 行）。拖动中的抓取基准要记录拖动开始时的 `BaseGrabOffset`／`BaseGrabNorm` 并由其推导每次转向，禁止在当前值上反复转置／夹取；`UColdSteelDragVisual::Configure` 会被重复调用，不能重建活动 widget 树。
- 落点要按"可见即所得"处理外层格：`PreviewItemDrag` 计算出的抓取锚点必须夹取进容器（列 `0…18-W`、行 `0…Rows-H`），否则光标停在最外一两列时，5 格宽枪械会一直报 `物品超出背包边界，请向内移动`，而用户会把它读成"转向把物品弄坏了"（实测日志 `INVDRAG` 证明转向状态当时完全正常）。夹取后高亮框即真实落点；`ColdSteelInventory::Move` 一侧保持严格规则不变（golden case 与视觉审计仍按模型行为断言）。

## 模态遮罩的光标会被"后来者的 BeginPlay"抢走（2026-09-25）

启动主界面（`TransitLoadingSubsystem::ShowStartupMenu`）看不到鼠标，但按钮仍可点。菜单本身逻辑没错：它设了 `bShowMouseCursor=true` 并 `SetInputMode(FInputModeUIOnly())`。真正原因是**执行顺序**——菜单在 `APlayerController::BeginPlay` 末尾调用，而 `AFPSGAMECharacter::BeginPlay` 更晚，它末尾无条件 `SetShowMouseCursor(false)` + `SetInputMode(FInputModeGameOnly())` 来恢复第一人称默认，把刚设好的状态覆盖掉。

**诊断口径：不要自己加日志，引擎已经把时间线打出来了。** `LogViewport` 有两条 Display 级日志：`Player bShowMouseCursor Changed, A -> B`（只在走 `SetShowMouseCursor()` setter 时打）和 `Viewport MouseLockMode Changed, ...`（每次 `SetInputMode` 都打）。按时间顺序 grep 本次运行日志，就能直接看出"谁在谁之后抢的"。注意**直接写成员 `PC->bShowMouseCursor=true` 不打日志**，所以"日志里没有 True->False 之外的变化"不等于没人改过。

5.8 的相关事实（别再按旧版经验找 `bHideCursorDuringTransition`，该字段在 5.8 已不存在）：

- `FInputModeUIOnly::ApplyInputMode` 会 `SetIgnoreInput(true)` + `SetMouseCaptureMode(NoCapture)`，**不会**因捕获隐藏光标；所以遮罩里额外调 `VP->SetIgnoreInput(true)` 是冗余的（无害）。
- `FInputModeGameAndUI` 相反：`SetIgnoreInput(false)`，且默认 `bHideCursorDuringCapture=true` 会写进视口客户端；`FSceneViewport::AcquireFocusAndCapture` 路径在鼠标按下时按该标志置 `bCursorHiddenDueToCapture`。需要"按下也不藏光标"的 GameAndUI 场景要显式 `SetHideCursorDuringCapture(false)`。

修法约定（比"在菜单里每帧重设"更干净）：

- 给遮罩一个**只读自身状态**的判据（`OwnsPlayerCursor()`：主界面或加载遮罩在挂），让所有"恢复玩法默认"的地方据此跳过。遮罩拆除时本来就会还原 `GameOnly` + 隐藏光标，跳过不留残余；两种先后顺序都成立。
- 遮罩侧把"只在首次夺光标"改成"**存续期间每帧夺回**"（`else if(!PC->bShowMouseCursor) PC->bShowMouseCursor=true;`）。地图旅行会生成新 Pawn，它的 `BeginPlay` 同样晚于遮罩，属同一类时序问题。
- 判据只读现有字段，不新增状态，避免遮罩与玩法各存一份"谁拥有光标"而互相不一致。

## 验证入口与失败判读



- `Tools/UI/run_drop_hitch_acceptance.ps1`：真实 Slate 键鼠输入，覆盖普通/独立菜单/拆分框关闭、拖出松手、TAB 取消、仓库内外点击及模型缓存。当前脚本要求 25 项全部执行并通过。
- `Tools/UI/run_inventory_drag_acceptance.ps1`：交换、堆叠、拆分、装备、快捷栏及保存回滚。运行前读当前脚本与审计源码；宿主可能含其他尚未发布的扩展阶段，不能用 Git 中较早的阶段数解释当前日志。
- 使用独立存档与本次日志核实结果；原生重编译后用新进程。检查不同分辨率的真实命中、焦点和数据，不以直接调用业务函数代替全部输入测试。
- 出现偶发中断时记录窗口激活事件、当前拖放操作、源实例位置及步骤；不能凭一次复测通过判定已修复，也不能没有事件证据就归因于窗口失焦。保留失败日志，不放宽成功断言或禁用失焦取消保护来消除测试失败。

历史证据：2026-09-11 的补修记录为 `Docs/UI/drop-hitch-and-backpack-close-20260911.md`，含三个分辨率各 25 项及最终 77 项拖放复测。一次快捷栏拖动中断当时未稳定复现，仍是观察项；这些数量不是当前运行结果或无缺陷保证。
