# 顶部生命／魔法栏与世界时钟

本轮交付为 UE 游戏接入与必要 Editor／Game 构建；未要求预览或测试，由用户测试。沿用冷钢 UI 2.3 和现有顶部事件栏。

## 结构与布局

- 顶部生命栏：生命、魔法两块等宽内容区，标签与当前／上限同排，下方实际填充条；右侧独立等级徽章。标准外框560×72px，与展开事件栏同宽。
- 右上时钟：标准286×72px，与生命栏同高、同顶边；52px太阳表盘，右侧突出HH:mm，另列第几日、阶段图形和晨曦／白昼／黄昏／深夜。保留game-dev独立时钟宽度，避免一长行日期挤出外框。
- 两者使用同一黑灰玻璃、10px圆角、1px细边和12px视口边距。生命魔法内卡不追加模糊，保留红／蓝资源语义色。
- 中文／普通UI使用Noto Sans SC；时间、资源量和等级使用JetBrains Mono。标签14px，资源量16px，等级／时刻20px，阶段辅助12px；DPI变化同步重设字体、控件与间距。
- 宽屏生命栏居中、时钟右对齐；空间不足时生命栏向左避让时钟并收窄。无法同排时，时钟放在生命栏下方靠右；事件进度栏从两者下方起排。生命栏宽不足480px时生命和魔法改为上下两行，等级保留在右侧，不整体缩小文字。

## 原项目参考与时间合同

参考只读game-dev的 `src/ui/panels/hud-panels-misc.js`（24小时表盘）、`src/ui/game-ui-manager.js:refreshGameTime`、`src/world/environment-lighting-system.js:getGameTime`、`game-style.css` 和 `ui/panel-theme-backpack.css`。

保留24个刻度、上下昼夜弧、地平线与太阳指针；上正午／右日落／下午夜／左日出。原项目相位0代表06:00，UE `AFPSWeatherManager::NormalizedDayTime` 的0代表00:00，因此先按同一UE日内时间解释，不能直接复制原相位。日序读取 `GetScheduleDay()+1`，阶段边界沿用05／08／17／20点。时钟与事件预报共用同一天气管理器，继承其天空同步、暂停和切换时间结果，不引入独立计时器、不读取电脑时间、不增加存档字段。

生命读取实际Pawn的 `UFPSCombatHealthComponent`；魔法及等级读取 `UColdSteelStatusModel`。缺失数值显示“—”；低生命保留原25%危险提示。无天气源时显示“--:--／时间未接入”，不伪造第1日。

## 所有权与文件

HUD持有生命栏与时钟控件；使用现有刷新节奏读取数据，只在时间文字变化时替换文本。时钟使用UWidget管理Slate表盘及文字，释放时重置Slate引用。全部为只读、不可命中的HUD，不注册新输入或改变鼠标／焦点；视口尺寸变化由HUD更新位置和尺寸。

修改 `ColdSteelTopVitals.cpp`、`ColdSteelHUDWidget.h/.cpp`、`ColdSteelEventTimeline.cpp`；新增 `ColdSteelWorldClock.h/.cpp`。复用当前字体、玻璃与资源条，不新增图片资源，无独立退役文件。本轮不运行旧Audit、不启动游戏或截图。

## 交付记录

2026-09-13 已完成上述代码接入。Editor 和 Game 的 Win64 Development 构建完成，日志为 `Saved/TopVitalsClock-editor-build-20260913.log` 与 `Saved/TopVitalsClock-game-build-20260913.log`。本轮编辑器模块为 `UnrealEditor-FPSGAME-913146.dll`；已打开的编辑器需重启加载原生代码。

未启动游戏、截图、执行Audit或运行测试；画面与交互由用户测试。

### 时钟对比度修正

用户反馈表盘颜色太淡、无法辨认指针。定位到Slate自绘圆盘只设置了画刷填色，传给 `MakeBox` 的最终颜色仍为白色；现改为显式传递 `Color * WidgetTint`，恢复真正的深灰表盘。

昼／夜弧线改为共享主题中的实色金／蓝，弧宽由1.8增至2.8表盘单位；指针由1.8增至3.2，追加5.8宽暗色轮廓、亮端点和独立轴心。昼夜阶段图形及文字跟随金／蓝语义色。表盘几何使用原48单位坐标，实际显示尺寸沿用52px。

本次 Editor／Game Win64 Development 构建完成，日志为 `Saved/WorldClockContrast-editor-build-20260913.log` 和 `Saved/WorldClockContrast-game-build-20260913.log`；编辑器模块更新为 `UnrealEditor-FPSGAME-913147.dll`。未启动游戏或测试，重启编辑器后由用户查看。
