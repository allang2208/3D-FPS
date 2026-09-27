# 火球待发射快捷槽白块修复

用户反馈火球凝聚后、尚未发射期间，快捷槽变白。

原因位于 `ColdSteelQuickSlot.cpp::NativePaint`：`IsPrepared()` 使槽位持续绘制金色边框；画刷本来采用透明填充，但传给 `FSlateDrawElement::MakeBox` 的填充色只有默认白色的 WidgetStyle Tint，没有乘以 `Brush.GetTint(Style)`。引擎直接使用传入的填充色，导致边框层以不透明白色覆盖图标。悬停与按键高亮共用同一路径。

修复仅为绘制颜色补上画刷 Tint，保留透明内部与金色边框。火球状态、技能图标资源、冷却遮罩，以及冷却完成时 0.6 秒的既定闪光均保持原逻辑。

FPSGAMEEditor Win64 Development 常规构建完成，`Saved/BuildEditor/QuickSlotHighlight20260927/native-build.log` 记录 ColdSteelQuickSlot.cpp 编译、UnrealEditor-FPSGAME.dll 链接和 Result: Succeeded。没有启动编辑器或进行游戏测试，实际画面由用户测试。
