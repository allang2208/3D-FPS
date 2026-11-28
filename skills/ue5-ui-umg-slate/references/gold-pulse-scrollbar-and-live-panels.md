# 冷钢金色脉冲滚动条与实时面板脏检查

**第一条（FPSGAME）　文件位置与引用路径。** 从[制作目录与功能索引](../../../Docs/Production/README.md)和[存储规则第 4.1 节](../../../WORKFLOW.md#41-存储分配与文件操作边界)查找功能入口，再确定制作源、正式资产与输出位置；交付时在同一功能条目登记位置和恢复版本。

共享实现：[ColdSteelScrollBar.h](../../../Source/FPSGAME/UI/ColdSteelScrollBar.h) / [.cpp](../../../Source/FPSGAME/UI/ColdSteelScrollBar.cpp)。

## 接入

- Slate 面板：`ColdSteelUI::ApplyGoldScroll(SAssignNew(Scroll, SScrollBox)..., Thickness, Padding, bEnsureVisible)`；UMG 面板用 `UColdSteelScrollBox` 或 `ColdSteelUI::ConfigureGoldScrollBox(UScrollBox*)`。不要在各面板复制一份近似的 `FScrollBarStyle`。为什么：全局只维护一份样式和一个动画器，颜色和节奏才能保持一致。
- 右上角的灵魂、货币胶囊和关闭按钮统一高度（当前为 `28 px`），新抽屉沿用 [SSiegeWorkshopMarket](../../../Source/FPSGAME/UI/SSiegeWorkshopMarket.cpp) 的头部结构。

## 动画器的开销边界

1. 专用服（`!FApp::CanEverRender()`）不注册、不建 Ticker。
2. 动画器 30 Hz 运行，但只对有效可见的滚动框做 `Invalidate(Paint)`。判定条件：祖先链上每一层 `GetVisibility().IsVisible()`、`GetTickSpaceGeometry()` 的尺寸大于 1 px，并且 `GetScrollOffsetOfEnd() > 0.5`（内容确实可以滚动）。为什么：只看滚动框自身的可见性，会让已收起但仍保留控件的面板每秒重绘 30 次。
3. 没有活跃滚动框时，跳过颜色插值和全部失效调用；所有滚动框都失效后移除 Ticker。

## 实时数值面板

`Tick` 内刷新的状态栏（耐久、等级、弹匣、换弹倒计时）先与缓存比较，只有显示值变化时才调用 `SetText`、`SetBorderImage`、`SetRenderTransform`；倒计时按 `0.1 s` 取整比较。`RefreshAll()` 重置缓存后强制刷新一次。为什么：`FString::Printf` 加上 `SetText` 每帧都会触发文本重排和布局失效，参见 [HUD InvalidationBox 缓存](hud-invalidation-caching.md)。
