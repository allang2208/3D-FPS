# 出征界面信息层级调整 2026-09-27

## 目标与范围
保留现有三栏、目的地选择、概览/奖励/规则页签和地下设施概念横幅。收紧任务信息阅读距离，突出准备状态与最终出征操作。使用 ue5-ui-umg-slate 和当前冷钢共享样式。

## 布局与样式
- 宽屏横幅172px，标题靠左下；紧凑或矮窗100px，沿用等比裁切和圆角。
- 任务概况改为推荐等级、探索规模、威胁情报、进入消耗四块信息卡。两列等宽，预计详情可用宽度低于560px时单列；改变窗口跨过断点时刷新详情。
- 行动提示独立浅底卡片，复用 StatusCard 背景；标题16px、正文14px、辅助12px，沿用工程字体入口和根DPI抵消。
- 右侧角色/武器卡、进入条件卡、同行成员单行说明。条件与底部状态都读取现有 BlockMessage，失败反馈优先于可出征提示。
- 底部固定显示目的地与实际消耗；可出征且无失败反馈时为绿色状态文字，确认按钮保留共享银白主操作色和禁用行为。
- 保留原三栏/两区/单页响应布局、内容独立滚动、固定页签及底部确认。

## 数据、状态与生命周期
数据仍来自 FColdSteelExpeditionDestination 和 ColdSteelStatusModel；选择刷新详情，OnChanged 刷新行前准备。Tick 只处理几何档位，不加载资源或解析物品数据。进入消耗缺失显示待公布；空列表、未选择、不可出征沿用原提示。ConfirmDeparture、控制器跳图、焦点、Esc返回、输入锁和Destruct解绑不变。不改战斗、存档或扣除逻辑。

## 文件与交付
修改 ColdSteelExpeditionWidget.h/.cpp 与 ColdSteelExpeditionLayout.cpp。不新增图片资产。
源码已落盘；本轮后台构建暂未执行：发现 FPSGAME 编辑器 PID 16988 运行，且已有 UBT/cl 构建占用。未停止任何进程、未触发第二轮构建。需要编辑器关闭且当前构建结束后完成正式构建。本轮未启动游戏、截图或测试，由用户测试。

用户关闭编辑器后执行正式构建。已修复本次新增 Slate 信息卡的两处闭合括号遗漏，出征源码编译通过。最终整体链接受其他瞄具改动阻塞：AFPSGAMECharacter::GetOpticMagnification 在 ScopeOpticalPresentation.cpp.obj 与 Module.FPSGAME.2.cpp.obj 重复定义（LNK2005/LNK1169）。日志 Saved/BuildEditor/build-20260927-203659.log。尚未生成成功的新 DLL，未修改其他任务的瞄具实现，未启动编辑器或测试。
当前源码仅有一份 GetOpticMagnification 定义，已更新 Editor 中间 unity 文件时间戳以触发重新编译，未修改瞄具源码。重试构建时编辑器进程重新出现，被 Build-Editor.ps1 安全阻止；仍需关闭占用后完成链接。

2026-09-27 20:43 续接：此前重复符号阻塞已解除。正式运行 Tools/Build/Build-Editor.ps1 返回 Result: Succeeded / Target is up to date，日志 Saved/BuildEditor/build-20260927-204304.log。当前构建产物已是最新；未修改瞄具源码，未启动编辑器或进行游戏测试。
