# 爆炸物危险提示 V05

用户已授权按两层提示方案制作。本次修正 V04 仅屏外有箭头、图标过小且整体衰减过淡的问题。

## 布局与数据

- 继续由 `ColdSteelHUDWidget::NativePaint` 调用独立 Slate 绘制器；复用 `UExplosiveWarningSubsystem` 的本地玩家 6 米过滤、10 Hz 遮挡/距离快照与紧迫性排序。
- 方向层：准星外围约 120 物理像素的圆周显示粗实心箭头。按相机水平朝向与玩家到囊弹的方位计算，前方在上、后方在下，不受俯仰或目标是否出屏影响。箭头附距离，同方向多枚附数量；最多 8 组，优先更紧迫目标，近似方位合并。
- 位置层：屏内囊弹上方显示 44 像素实心囊弹符号、深色半透明底板、对比描边、引信剩余圆环和距离。避开准星及方向层，用细引线指回真实投影位置。屏外/背后由方向层承担提示，不再把图标挤在屏幕边缘。
- 位置重叠时合并计数，最多 8 组；图标主体与方向箭头始终不透明，脉动只作用于外圈。爆裂后立即停止绘制，不等待快照刷新。
- 宽/高不足时收拢方向圆半径，位置标记按当前玩家视口留边；使用物理像素与 DPI 换算，数字使用共享 JetBrains Mono。无警告时无绘制，不创建 Widget 或接收输入。

## 语义与资源

- `ColdSteelUI::Warning` 表示附近囊弹，`Danger` 表示已触发引信、无遮挡且玩家处于真实伤害范围；有墙/楼板遮挡使用 `TextSecondary`。不把预警范围当作伤害范围。
- 使用共享黑灰底色、银白实心图形与危险语义色，不对整体控件降透明度。引信圆环直接读取 `FuseProgress()`，不另设动画计时器。
- 仅参考 EasyIndicators 的屏内/屏外分离思想。本版图形和实现为项目自制，没有安装 Unity 插件、复制第三方源码或导入其资源。
- 沿用投射物注册/注销及世界结束清理。无新快捷键、输入焦点、存档字段或伤害行为。

## 文件和接入

- 实现：`Source/FPSGAME/UI/ColdSteelExplosiveWarnings.cpp`。
- 本文记录布局、数据和交付边界；V04 声音、爆炸特效、动作与数值继续沿用。
- 接入准备时编辑器已退出，互斥桥连接被拒绝；未执行 Live Coding。随后使用常规后台 Editor/Game 构建，不启动新编辑器。

## 实际交付

- `FPSGAMEEditor` Win64 Development 构建成功：`Saved/BellowSacLobber20261012/build-warnings-v05-editor-final.log`，`Result: Succeeded`，已链接 `UnrealEditor-FPSGAME.dll`。初次构建的相机 TObjectPtr 自动类型推导问题已改为显式指针类型。
- `FPSGAME` Win64 Development 构建成功：`Saved/BellowSacLobber20261012/build-warnings-v05-game.log`，`Result: Succeeded`，已链接 `Binaries/Win64/FPSGAME.exe`。
- 两层绘制均已接入原有 HUD 调用，无蓝图或美术资产等待导入；没有变更引信、伤害、怪物动画或 V04 声音。
- 绘制器一次提交实心图形批次；每层最多 8 组，空列表直接返回。保留现有 10 Hz 查询，绘制只读取快照和当前投影；未测量帧率收益。
- 未启动编辑器、PIE、游戏、截图、渲染预览或自动测试。下次正常启动使用新版；实际观感由用户体验。
