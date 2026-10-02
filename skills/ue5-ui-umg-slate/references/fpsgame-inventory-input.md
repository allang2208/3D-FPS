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

## PlaceDisplaced 行掩码必须跟当前背包行数走（2026-10-01 崩溃修复）

- `PlaceDisplaced`（ColdSteelSwapPlacement.h）按 `Rows` 参数分配行占用掩码 `Occupied.Init(0,Rows)`，再扫**全部**同 Place 物品写 `Occupied[Cell/18+Y]`。背包行数变成装备驱动（便携背包 +1 行）后，`Move` 里两处调用传默认 `Rows=4`：一个跨在基础 4 行边界上的物品（如 1×2 卡在 70/71 格，占 3、4 两行）会写 `Occupied[4]` → `Array index out of bounds: 4 into an array of size 4`，拖动悬停预览即崩。
- 修法两件事都做：调用点一律传 `BagRows(Items)`（用**事务前**的数组算——替换背包的流程里守卫已保证新背包覆盖现有占用）；`PlaceDisplaced` 本体对掩码写做 `Row<Rows` 钳制（跨行物品只会溢到更高行，那里不产生候选位，钳掉既防崩又不漏正确占用）。
- 教训：**给"写死 4 行"的背包加装备驱动扩行时，凡是按 `Cell/18` 索引行数组的扫描都要重审**——占用掩码、行循环上界、数组大小三处必须同源。仓库侧 `WarehouseRemainingCapacity` 的同类数组因物品不能跨页而天然安全。

## 装备替换回填的自动朝向（2026-09-27）

- 右键装备、拖到装备槽以及自动卸下时，旧装备回填可尝试两种朝向；手动拖到明确背包格子时保留玩家选定朝向。不要把自动旋转加进所有调用共用的 `Insert`，以免改变手动摆放语义。
- 先尝试原有朝向的完整布局，失败再开放旋转。双手武器挤出的主／副手一起规划，不能让第一个贪心落位占掉第二个唯一可用矩形。候选记录实际宽高、旋转状态和行位掩码，回溯失败完整撤销占位。
- 优先使用新装备腾出的区域，再找附近连续空位；装备槽编号不是背包坐标，不能参与格子相对偏移。搜索预算耗尽与空间不足返回不同原因，事务失败不发布半成品布局。
- 悬停高亮与提示读取同一次 proposal 中旧装备的最终 Cell／Width／Height／bRotated，确保预览与提交一致。当前入口 `ColdSteelSwapPlacement.h`、`ColdSteelInventoryRules.cpp` 和 `ColdSteelInventoryWidget.cpp`；见 `Docs/UI/equipment-backpack-auto-orientation-20260927.md`。

## 背包内"数字快捷栏"整块退役（2026-10-01）

- 背包抽屉底部的"数字快捷栏"四槽镜像（标题、"技能 / 消耗品"角标、四槽位、下方"拖动放置 / 交换物品""单击查看…"两行静态说明，以及抽屉 UMG Footer"Tab 收起…"行）已按用户要求整体删除；`FBoardLayout.HotY` 语义收窄为"背包格底缘/落款锚点"，背包高度 `HotY+34`，仓库分支布局未动。
- 随块删除的交互：`Hit` 的 Place==3 区、右键解绑、双击 `UseHotbar`、槽位 `StartQuickDrag`/`DropQuickDrag`、键盘 F 焦点轮换的快捷栏站与 Space 搬运解绑、`UColdSteelItemDrag::HotbarIndex` 字段（HUD 级 `CanDropOnHotbar`/`NativeOnDrop` 的换绑分支一并退役）。
- **真快捷栏（HUD 底部 ColdSteelQuickSlot/HotbarDrag/SkillPage）零改动**：背包格子拖到真快捷栏绑定（`BindQuickItem`）、槽间拖动交换、拖出解绑、技能页拖入绑定全部保留；模型层 `BindHotbar/SwapHotbar/UseHotbar/ResolveHotbar` 服务端能力不动（`ColdSteelInventoryAudit` 的模型级用例照旧）。
- 反馈行改为**只在有内容时绘制**（PreviewReason／InteractionMessage／已选中），默认态背包底部无文字；静态操作说明不再恢复。仓库页保留"单击查看 · 右键取出"说明行。
- 审计同步：`ColdSteelInventoryDragAudit` case 5 删去两条快捷栏搬运用例；VisualAudit/GlassAudit 的底部内容锚从 `HotY+85` 收到 `HotY+34`/`HotY+30`。跑拖放验收前先读当前脚本阶段数。

## 背包装备与夹层（Place 5，2026-10-01）

- 便携背包（`ue_portable_backpack`，`equipSlot:"backpack"`＝装备栏 14 号"背包装备"槽）用两个字段撑容量：`bagExtraCells`（每 18 格＝主背包加一行）与 `bagCompartmentCells`（夹层容量，≤36）。没有建模/贴图，无 `ue_icon` 时背包卡片显示名字文本。
- 容量全部由装备的背包物品派生：`ColdSteelInventory::BagRows/CompartmentCells/EquippedBag`（Rules.cpp）每次扫 14 号槽占主并读其 Data（`ColdSteelItemData::Read` 按载荷缓存）。`Owner` 的背包分支已去掉 `Cell<72` 写死界（改纯几何匹配），行数边界由 `Fits`/调用方裁剪；**加载校验 `ValidateProfile` 必须先按整表算 `ProfileBagRows/ProfileCompCells` 再逐件校验**——装备栏条目在 Items 数组里可能排在夹层/扩展格物品之后，逐件动态算容量会顺序漏判。
- 夹层＝`Place 5`，**网格尺寸＝长×宽（列×行）由装备的背包定义**（`CompartmentGrid`，缺省 6×6，上限列 18/行 24，容量＝列×行；约定详见 item-asset 技能的 backpack-equipment.md）。转移规则在 `ColdSteelCompartmentRules.cpp` 的 `Transfer`（网格作参数传递）：目的地 5（夹层内挪动/放入）、0（放回背包，Cell -1 自动寻位带旋转重试）、1（直接穿装备）；单件占用＝交换（被压物品回到来源腾出的位置，放不下整次取消）；来源可为 0/1/4（仓库 `Transfer` 已放行夹层来源，仓库↔夹层拖动靠共享板 DragOver 命中夹层区）。模型侧 `ProposeMove` 按"目标或来源是 5"路由到 `ProposeCompartment`。
- **14 号槽占有者变更保护**（Rules.cpp `Move` 内）：卸下或替换背包时，夹层物品与扩展格（Cell≥新行数×18）物品必须能被更换后的背包继续容纳，否则拒绝（"夹层还有物品，先清空再卸下背包"）——否则存档出现越界孤儿，加载校验整档拒绝。夹层里的背包本身（槽14→夹层）在 `Transfer` 顶部单独拒绝。
- UI：`FBoardLayout.CompY`（0＝无夹层）在 `Layout()` 里按 `CompartmentCells>0` 追加区块，面板高度随之伸缩；绘制与"空间背包"同款版式（标题"夹层"＋右侧"X / 36 格 · N 件"＋分隔线＋进度条＋6×6 网格），`Hit` 增加夹层命中（Place 5），拖放/悬停/浮窗走通用链路，浮窗位置行显示"夹层"。
- 夹层与背包同权（2026-10-01 第二轮）：夹层头部有"整理"按钮（`SortCompartment`，大件优先/类别+名称，空夹层给提示）；Shift 单击/浮窗均可拆分（`Split` 按落点容量找格，浮窗文案"确认后放入夹层空位"）；制造/熔炼/建筑材料（`ConsumeItem`/`CountMaterial`/`ConsumeMaterial`）/强化卷轴与费用（BackpackOnly 视夹层为随身）/献祭/快捷栏绑定解析（`ResolveQuickItem`）全部把 Place 5 计入消耗域，扣减顺序 背包→夹层→仓库；右键/双击与背包同语义（消耗品直接用、装备直接穿——`Compartment::Transfer` 支持 Destination 1，被换装备回夹层原格）；背包格拖到真快捷栏绑定消耗品也接受夹层来源（`CanDropOnHotbar`）；键盘 F 轮换 背包→装备→夹层→背包（未装备带夹层的背包时不进夹层站），方向键夹层按 6 列、Space 搬运通用。
- 卸背包自动搬家与快捷栏并堆（2026-10-01 第四轮，同日修订卸下规则）：槽14更换/卸下时，夹层中超出新容量的物品随**同一事务**搬进背包（`Insert` 会并入同类堆），扩展格里放不进新行数的物品也自动回落重排（优先原列底部）；连同放回的背包本体一起装不下则整体拒绝（"背包空间不足，无法卸下背包装备"），不发布半成品——判据是"收缩后无法存放才拒绝"，不是"扩展格有物品就拒绝"。**所有能让背包离开槽14的通路都要防宿主丢失**：`Move`（迁移）、`Drop`（丢地面，拒绝）、仓库 `Transfer`（存仓库，拒绝）——漏一条就会在下次加载时因夹层容量=0 而整档校验失败。快捷栏把背包+夹层的同类消耗品视为一体：`QuickItemCount` 显示合计，`ResolveQuickItem` 按背包→夹层优先解析消耗目标（背包堆耗尽实例移除后自然落到夹层堆），绑定按 Definition 不按实例，换堆不失效。
- 夹层拖拽对齐（2026-10-01 第三轮）：夹层目标的落点预览走**独立分支**，与背包同口径——高亮框按抓取锚对齐（`HoverCell%Columns-GrabOffset`，钳到 `Columns/Rows-PreviewCells`），悬停被占格时换到该物品锚点预览交换；超出夹层尺寸给"这个朝向需要 X×Y 格，夹层只有 6×6"提示。**从夹层发起**拖动时 `NativeOnDragDetected` 的 `GrabOffset`（按 6 列算）与幽灵贴图基准 `Origin`（CompY+6 列）都要按夹层坐标算，否则幽灵锚点乱跳、预览错位——背包/装备/仓库来源的公式不能直接套。
- 夹层来源可转向：`RotateDraggedItem` 的来源白名单（0/1/4）要加 Place 5，F 转向才对夹层拖出的物品生效；落点侧 `Compartment::Transfer` 已按 `ApplyOrientation(Orientation)` 提交待定朝向，两侧对称。
- **ProposeMove 路由顺序（2026-10-02 修复）**：目标是夹层(5)必须**先**判进 `ProposeCompartment`——仓库物品拖进夹层若先撞上 `I->Place==4` 的仓库分支，`Warehouse::Transfer` 只认目标 0/1/4，会以默认文案「空间不足」静默拒绝（预览与落点同错）。反方向 `来源=5 且目标=4` 仍归仓库规则（夹层 Transfer 不支持目标 4）。仓库来源的交换回填与并堆余量必须带上源容器容量与原朝向（`Transfer` 追加 `WarehouseCapacity` 参数，余量/回填还原 Container+Width/Height+bRotated）。
- **储物容器会话分域（2026-10-02 宝箱排查）**：地牢宝箱/储物箱 = `Place 4` + `Container` 键，经 `BeginStorageSession` 绑定到仓库面板，`InOpenStorage`/`Owner` 只对 Place 4 按容器过滤。凡修改 Place 4 物品的入口都必须校验 `Item.Container==ActiveContainer`——`Warehouse::Transfer` 自带；`ProposeCompartment`、`Drop`、`Split` 在模型层各有一道补齐的门，否则关着的箱子会被夹层通道/丢地/拆分借道抽空或写坏格位。箱内弹药取出（目标 0 **或** 5）统一走 `ConvertChestAmmoToPool` 转弹药池，两个入口（`MoveItem`/`TransferWarehouse`）的判定条件要保持一致。
- 夹层复查批（2026-10-01 回头检查，5 处修正）：(1) `Compartment::Fits` 必须把 Grid **透传给 Owner**（`Owner(...,FString(),Grid)`）——加载校验时装备栏可能还没进 Placed，Owner 自推导得零网格会跳过重叠判定漏放坏档；(2) `NativeOnMouseLeave` 与 `bSortHovered` 一起复位 `bCompSortHovered`，否则悬停离开后残留，点空处误触"整理夹层"；(3) 卸下/换装事务里所有网格边界（Move 的落点边界、被换装备的 PlaceDisplaced 回填、换装落格 Fits）一律用**移动后行数**（BagChangeRows/RowsAfter），用装备中行数会让矮物品落进即将消失的扩展行成坏档、或换大背包时误拒；(4) 仓库打开时 `DefaultAction` 的存入分支要含 Place 5（右键菜单"存入仓库"按钮才名实相符，底层 WarehouseRules::Transfer 已放行夹层来源）。通用教训：**容量装备驱动化之后，凡事务中途计算"当前容量"的地方都要问一句——这算的是移动前还是移动后？**
- 命名空间坑：没有 `using namespace ColdSteelInventory` 的文件（如 ColdSteelQuickBarModel.cpp）里，`ColdSteelCompartment::Place` 必须全限定 `ColdSteelInventory::ColdSteelCompartment::Place`，否则 C2653；UBT 控制台会吞真实错误，去 UnrealBuildTool 的 Log.txt 看。


## 滚轮翻页与会话行门控（2026-10-02）

- **滚轮翻页**：储物面板的 SScrollBox 要 SetConsumeMouseWheel(EConsumeMouseWheel::Never) 让事件冒泡到 UserWidget；NativeOnMouseWheel 内 Pages=Max(1,OpenStorageCapacity()/CellsPerPage)，WarehousePage=(Page+dir+Pages)%Pages 取模循环（上滚=前页、下滚=后页、首尾环绕），翻页后 Board->ResetStoragePage()+Scroll->ScrollToStart()+Refresh()。页数容器感知，主仓库/储物箱/宝箱各自适配。
- **储物会话门控**：UColdSteelWarehouseWidget::SetLootSession(bool) 区分——OpenWarehouse（主仓库+储物箱家具）显示功能行（全部存入/取出同类/存入同类/整理下拉），OpenChestLootStorage（地牢宝箱）折叠。批量操作本体容器感知（ActiveContainer/InOpenStorage/OpenStorageCapacity），恢复 UI 时不用改模型层。
