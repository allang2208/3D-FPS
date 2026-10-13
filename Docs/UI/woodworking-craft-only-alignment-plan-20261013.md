# 木工台：锯齿标识对齐、仅正式制作与纯木板

## 目标与布局

按用户反馈修正偏到屏幕右侧的锯齿红色提示，取消练习/挑战，只保留正式制作，并删除木板上的金属夹片。保留选择卡片、预览/材料/条件卡、底部进入卡片及横排文字规则；底部取消模式选择，只显示制作入口。

## 显示与输入

- 红色锯口提示改为实景几何，直接挂到设备的 WoodworkingSawPivot 插槽；切割状态沿露出木板的锯齿圆弧显示红色边缘，调整状态在木板上表面显示落刀虚线。使用既有标记材质和少量动态网格，随台锯、相机、缩放一起渲染，不再叠加另一条屏幕投影红线。
- 移除运行时木板网格追加的握柄、两片金属卡扣，以及二维表示与隐形点击区域；仅保留真实木板抓取，维持移动、1°/0.25° 旋转与暂停调整功能。
- 指示网格仅在准备/切割状态切换时更新，不做逐帧全量重建；材质仍沿用异步加载，不新增资源文件。

## 制作与状态合同

- 使用已有正式配方目录过滤可选图样。目前只有弓臂正式配方（2 木材制作 1 弓臂）；未配置正式配方的旧练习图样不出现在选择目录。
- 面板始终使用 Craft；系统拒绝旧 Practice/Challenge 模式与无工作台的练习入口。旧枚举值和函数签名暂留兼容已接入网络操作编号，不能从旧入口启动无消耗制作。
- 材料不足或背包容量不足沿用现有报价禁用开始；进入后先调整，切割期间计时，调整时暂停；达标领取时一次扣料。损伤与清除阈值、成品配方、存档结算不改变。

## 文件与交付

限定修改 WoodworkingWorldView、WoodworkingSystem、ColdSteelWoodworkingWidget、WoodworkingPanel、ColdSteelWoodworkingController、FPSGAMEPlayerController 的旧练习命令声明与 woodworking.json 的说明。备份与构建记录：Saved/WoodworkingCraftOnly20261013。

沿用现有 UE C++ 与冷钢 UI 工作流，完成必要后台构建；不打开 UE，不运行游戏或测试。实机标识位置和手感由用户确认。

## 当前落盘状态

- 源码已改为锯片插槽上的实景红色弧线/调整虚线，并移除 Slate 的屏幕投影标识。
- 握柄与两片金属夹片的生成代码、额外的抓取区域及二维握柄表示均已移除；视角取景改为实际木板范围。
- 正式配方过滤、仅 Craft 可开始、界面模式按钮移除和旧 WoodworkingPractice 控制台入口移除均已落盘；现有正式产物为弓臂。
- 用户关闭编辑器后，FPSGAMEEditor Win64 Development 常规构建返回 Succeeded（退出码 0）；等待已有构建结束后，UBT 确认目标已是最新。日志：Saved/WoodworkingCraftOnly20261013/Editor-build.log。
- FPSGAME Win64 Development 常规构建返回 Succeeded（退出码 0），FPSGAME.exe 已链接并落盘。日志：Saved/WoodworkingCraftOnly20261013/Game-build.log。其他并行修改保留。
- 构建产物与源码记录保存在 Saved/WoodworkingCraftOnly20261013/delivery.json。本次使用已有材质与运行时网格，没有新增待导入或待编辑器保存的资产。
- 没有打开 UE、运行游戏或测试；实机标识位置、制作流程和操作效果由用户测试，编译成功不代表实机验收通过。
