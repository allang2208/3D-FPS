# 鼠标滚轮切换双武器栏

游戏输入模式下，滚轮上/下均通过 `UColdSteelStatusModel::CycleWeapon()` 切换装备槽 6 与 9，与原 G 键一致。只响应 MouseScrollUp/MouseScrollDown 的 IE_Pressed，忽略释放和 Repeat，未绑定 MouseWheelAxis，避免同次滚动重复切换。UE 本机 `SceneViewport.cpp` 的 OnMouseWheel 确认物理滚轮会产生这两个方向键的按下/释放事件。

沿用原装备事务、弹药保存和角色换枪动画。另一武器栏为空时保持当前武器；背包打开时不由滚轮切枪，天气、枪匠及强化界面继续使用已有输入拦截。未新增 Blueprint API、网络同步或逐帧工作。

Editor Development 编译成功（本次构建后缀 2357）。并行构建随后更新了模块清单；新独立游戏进程实际加载 `UnrealEditor-FPSGAME-2026092045.dll`，通过新增验收确认其中已包含本次滚轮逻辑。`-WeaponWheelAudit -ColdSteelProfile=WeaponWheelAudit_20260910_v1` 在隔离存档中用真实 PlayerController InputKey 路径测试 AKM/M4 双栏，12 PASS、0 FAIL、进程退出码 0。覆盖双向切换、相同方向切回、释放/重复事件、12/17 发弹药保持、背包双向滚动、原 G 键、另一栏为空。记录位于 `Saved/WeaponWheel20260910/runtime-v1.log`，两张实际截图位于同目录。

验收实现在 `Source/FPSGAME/WeaponWheelAudit.cpp`，仅显式开关启动。用户原有编辑器未被关闭，需重启后加载新模块。
