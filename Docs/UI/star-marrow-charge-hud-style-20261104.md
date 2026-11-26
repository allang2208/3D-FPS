# 星髓长锋充能 HUD 下移与冷钢样式

用户要求：充能能量条下移，刻度与说明使用主界面金色及坐标罗盘字体。

充能仍由准星覆盖层中的 `ColdSteelStarMarrow::Paint` 绘制，沿用 `UStarMarrowComponent` 的可见状态、剩余时间、淡出和动态材质。图像顶部先从视口中心下方 44 px 调整至 108 px，再按用户要求下移 64 px 至 172 px，常规窗口下累计下移 128 px；经验提示同量让位。矮窗口共享同一个布局缩放，保留底部空间。没有新增交互控件、输入焦点、资源加载或玩法写入。

刻度与说明复用 `HUDGold / HUDGoldLight / HUDGoldDim`；标题、按键及倒计时使用罗盘主刻度同源的 `NumberFont` Medium 16 px，百分比刻度使用罗盘次刻度同源的 Regular 11 px。JetBrains Mono 的中文由现有 Noto Sans SC 回退字体承担。显示内容保持横向单行，颜色沿原有淡出透明度更新；蓝色能量材质与动态火焰沿用现有资源。

修改范围：`ColdSteelStarMarrow.h/.cpp`、`ColdSteelExperienceFeed.cpp`。本轮仅执行必要后台构建，不运行游戏、截图或 UI 验收；实际位置与可读性由用户体验确认。

首次下移 64 px 的后台 `FPSGAMEEditor Win64 Development` 完整构建成功，基础 DLL 已更新。构建日志：`SourceAssets/StarMarrowChargeMotion20261103/build-editor-20261104-001548.log`。追加下移 64 px 也已完成后台完整构建并更新基础 DLL，日志：`SourceAssets/StarMarrowChargeMotion20261103/build-editor-20261104-090444.log`。未启动编辑器或进行游戏测试。
