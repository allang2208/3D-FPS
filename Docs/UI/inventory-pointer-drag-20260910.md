# 背包拖动贴图跟随修复

用户报告枪械拖动出现从装备栏飞向背包的错误动画。当前 UE 5.8.2 的 `UMGDragDropOp.cpp` 对 DefaultDragVisual 固定执行 150ms 起始插值，起点是源 UUserWidget（整个背包板）的左上角，不是被抓取物品的位置。项目的 `NativeOnDragOver` 又持续改写 Offset，把贴图吸附到目标格，形成起拖飞入与移动跳格。

背包板继续通过 UDragDropOperation 接收 Slate 拖放事件，数据仍走原有 proposal/commit。新的 UColdSteelDragVisual 是只绘制图像的视口层，不接受命中或键盘焦点。默认 UMG 拖动装饰器留空，视口层按 Dragged 事件更新，不使用插值、Tick 轮询或材质捕获。图像使用当前实例的模型贴图，大小及抓取点按照源格真实绘制范围计算，装备格和背包格之间不变形、不吸附；落点高亮仍按背包格与交换规则计算。

指针使用桌面坐标，视口绘制需要通过 GetViewportWidgetGeometry 转换，再按绘制层尺寸换算 DPI。源物品保持淡出，手中图像不透明度提升至 0.9。松开、取消、关闭面板与销毁背包板时移除视口层，释放引用。

新增 `Tools/UI/run_inventory_visual_acceptance.ps1 -DragVisual`，通过实际 Slate 鼠标按下、移动和松开，覆盖装备到背包、背包到装备、起拖首 150ms 连续位移、抓取点/图像尺寸保持、取消与关闭清理，并检查操作前后实例数据、弹药与快捷栏不变。测试抓取点避开装备格二等分的浮点边界。截图输出 `Saved/InventoryVisual/drag-start-*.png`、`drag-to-bag-*.png`、`drag-dropped-*.png`、`drag-to-gear-*.png`。

UE 5.8.2 Editor Development 编译通过（最终模块后缀 `2026092047`，禁用 UBA 重建本次修改，避免共享增量产物未带入新代码）。1280×720、960×540、1920×1080 的真实鼠标拖放各 17 项通过，截图逐档检查图像显示和位置。日志为 `Saved/InventoryVisual/20260910230153-1280.log`、`20260910230456-960.log`、`20260910230456-1920.log`。小窗口测试先滚动到源武器及目标格均可见的位置。

`run_inventory_drag_acceptance.ps1 -Widths 1280 -Quick` 通过 77 项，包括 3750 个既有规则样例、枪械与药水交换、多个物品回填、快捷栏绑定、拖出/返回面板及取消；日志 `Saved/InventoryDrag/20260910230653-1280.log`。所有测试使用独立审计存档。已有编辑器需重启后加载新的原生模块。
