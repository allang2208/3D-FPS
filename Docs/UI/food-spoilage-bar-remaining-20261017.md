# 食物腐败条改为剩余鲜度 · 2026-10-17

用户要求：背包栏中的食物腐败条一开始是满的绿色，随时间逐渐减少，颜色转黄、红。

## 范围与表现

| 入口 | 内容 |
| --- | --- |
| 空间背包、夹层、仓库、共享储物格 | 共用 4px 食物条，位于物品卡片底部内侧 |
| 物品浮窗（悬浮与固定详情） | 同一数据源的 4px 条，无时间／百分比文字 |
| 已到期的旧食物 | 仍由权威事务转换为腐败食物；转换前保留红色最低填充 |

- 旧表现：填充宽度 = 已消耗寿命比例（新鲜时为空，随腐败增长到满条）。
- 新表现：填充宽度 = 剩余鲜度（新鲜时满条，随时间缩短到空）；颜色仍按已消耗寿命的阶段：已消耗低于 50% 为 `Success` 绿，50% 至低于 80% 为 `Warning` 黄，80% 及以上为 `Danger` 红。
- 条最低保留 2px 可见填充，避免接近过期时整条消失。
- 浮窗与卡片同向；不新增文字、倒计时或百分比。

## 数据与刷新

- `SpoilProgress`（卡片）与 `FoodProgress`（浮窗）继续表示已消耗寿命，数据、审计和存档口径不变。
- 绘制时统一调用新增的 `ColdSteelFoodUI::Remaining()` 取剩余比例；不改食物时钟、堆叠、转移、使用、腐败转换或联机事务。
- 可见食物沿用每秒一次的展示缓存刷新；浮窗只更新同一进度条，不重建列、不重新读目录或加载资源。输入、焦点、视口避让与销毁行为沿用原控件。

## 文件

- `Source/FPSGAME/UI/ColdSteelFoodPresentation.h`：新增 `Remaining()`，说明 `Progress()` 与 `Color()` 的方向。
- `Source/FPSGAME/UI/ColdSteelInventoryPresentation.cpp`：卡片条按 `Remaining()` 绘制，2px 最小填充替代旧起点标记。
- `Source/FPSGAME/UI/ColdSteelItemTooltipLayout.cpp`：浮窗条按 `Remaining()` 绘制，颜色仍按 `FoodProgress` 阶段。
- `Docs/UI/ui-cold-steel-design-system.md`、旧的食物条规划／实现记录同步补充替代说明；`Docs/UI/README.md` 增加索引。

## 构建与测试

- 必要构建：`ColdSteelInventoryPresentation.cpp`、`ColdSteelItemTooltipLayout.cpp` 已编译（Editor 对象 22:40），并已链接到 22:44:54 的 `Binaries/Win64/UnrealEditor-FPSGAME.dll`；本次补跑 `FPSGAMEEditor` 报告 `Target is up to date`／`Result: Succeeded`，日志 `Saved/BuildEditor/food-bar-remaining-20261017-editor.log`。
- 并行构建阻塞：`FPSUDSBridgeComponent.cpp` 的局部变量 `Object` 在 `else if` 中重名，C4456 使全模块构建失败；已做一行改名（`Component`），不改变曝光参数识别逻辑。该修复属于解除构建阻塞的最小改动。
- 预览／检查／测试：用户未要求，未执行；不启动游戏、PIE、截图或验收，实际卡片／浮窗观感由用户测试。
