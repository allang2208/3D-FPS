# HUD 金色圆角分辨率错位修复 2026-09-27

用户报告不同分辨率下四角金色圆边错位。

- PaintHUDNavigation 在 Super::NativePaint 完成子控件绘制之后运行，装饰改用目标控件 GetPaintSpaceGeometry，直接通过目标 ToPaintGeometry 绘制局部圆弧，去掉 tick 缓存坐标到 HUD 的二次变换。
- UBorder 装饰读取实际 Brush.OutlineSettings.CornerRadii，不再对所有面板统一假设 10/PixelScale；快捷栏本体为固定 Slate 半径，原假设在非 1 DPI 下不匹配。
- 生命面板跟随实际 TopVitalsTint 表面，而非外层布局包装。
- 当前修改不改变 HUD 锚点、内容、交互与刷新频率。

编译结果：Live Coding Success，当前编辑器已应用修复，日志 Saved/BuildEditor/hud-corners-dpi-live-result2.txt。常规 DLL 尚未重编译；未进行多分辨率实机截图测试。
