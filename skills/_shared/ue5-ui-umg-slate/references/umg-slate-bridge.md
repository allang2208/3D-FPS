# UMG + Slate Bridge Pattern

## When to Use
- Use UMG for layout, animation, and designer iteration. 原因：布局和设计动画可沿现有 UMG 控件组织，选择仍以当前面板架构为准。
- Use Slate for custom drawing, dense grid logic, or low-level input handling. 原因：底层绘制与输入可直接使用 Slate，避免为这些需求额外堆叠布局控件。

## Bridge Shape
- `UWidget` host class owns `TSharedPtr<SWidget>`.
- `RebuildWidget()` creates Slate instance.
- Blueprint API on host widget forwards data/config to Slate widget.

## Data Updates
- Prefer event-driven refresh from gameplay component delegates. 原因：已有状态变更事件能直接定位刷新时机，避免界面反复查询未变化数据。
- Avoid per-frame polling when data change events are available. 原因：数据未变时轮询不产生新显示内容，事件驱动可减少高频重复计算。
