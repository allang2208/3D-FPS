# 背包拖出至底部快捷栏 · 2026-09-10

参考：Godot `ui/backpack_hud.gd:858` 以 instance_id 绑定快捷栏，`_notification` 保存拖动原区域，`_profiled_process` 在拖出时提升快捷栏层级。现存 Godot 代码没有自动隐藏背包；本次按用户要求新增这一表现。

实现：UMG DragDropOperation 的 Dragged 事件按拖动起点时的整个背包面板屏幕边界判断。越界只隐藏面板、遮罩和模糊效果，保留拖动、面板布局及 UI 输入锁；回到原区域立即恢复。底部 1–4 号格沿用原冷钢外观，在拖动期间升到可接收层级。落位以真实格子 geometry 定位，通过现有 StatusModel.BindHotbar / SwapHotbar 保存实例绑定。物品继续占原背包格、数量不变；装备/失效来源不能绑定。

结束/取消/失焦恢复面板与快捷栏层级。落在无效区域仅结束拖动。原背包布局、容量、穿脱、内部移动和物品菜单保持原有行为。未修改 Godot 文件和游戏物品持久化算法。

源文件：新增 Source/FPSGAME/UI/ColdSteelHotbarDrag.cpp，调整 ColdSteelHUDWidget.h/.cpp、ColdSteelInventoryWidget.h/.cpp，以及既有 ColdSteelInventoryDragAudit.cpp。
原件及散列：trash/hotbar-external-drag-20260910/。

验证通过后在此记录真实结果；所有运行使用独立 InventoryDragAudit 存档。

显示实现使用 ESlateVisibility::Hidden 保留原布局边界；不单靠父控件透明度，因为背包自绘格子不继承其淡出效果。快捷栏在整个拖动期间提升层级，以使位于原面板区域内的 3/4 号格同样可投放；指针在面板范围内时面板依然可见。松手、取消、应用失焦后恢复原层级，取消失焦事件订阅。

原生编译：Development Editor 模块 2026091092，Succeeded。1280×720 真实拖放验收已完成 58 项零失败，实际截图确认完整隐藏与恢复。

最终验收：960×540、1280×720、1920×1080 三档各 58 项零失败，进程均退出 0。逐档实际截图检查拖出完整隐藏、拖回显示、快捷格绿色高亮和松手后恢复。每档实际鼠标操作覆盖全部四个底部格，包括与原背包范围重叠的格子；物品位置、数量、实例绑定和重载均正确。既有内部拖放、拆分菜单、右键穿脱及取消检查继续通过。失焦取消、装备拒绝绑定和失效来源拒绝检查通过。没有执行打包验收。

最终日志：SourceAssets/HotbarExternalDrag20260910/20260910161200-{960,1280,1920}.log。预览同目录 external-{outside,return,hover,bound}-{width}.png。
当前打开的 UE 编辑器仍持有旧模块；重启编辑器后加载新编译结果。
