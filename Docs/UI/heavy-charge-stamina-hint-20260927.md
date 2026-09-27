# 重击蓄力体力条提示 2026-09-27
复用 ColdSteelStaminaHUD 的 DashAttackReadyText、位置与 DPI 布局。脚架原优先级不变；近战提示优先读取 HeavyChargeFraction，蓄力时显示0–99%文字，完成显示100%，结束后恢复冲刺提示或隐藏。共享14px字体、灰色进行中/银白完成，不增加控件、计时器或资源加载。真实进度沿用武器按技能蓄力时长归一化的值；不改变蓄力、释放、自动释放、伤害或体力规则。
修改 Source/FPSGAME/UI/ColdSteelStaminaHUD.cpp。编辑器 PID 54524 正在运行，常规构建待关闭后完成；未启动测试或游戏。

已随成品预览分栏完成正式构建：Saved/BuildEditor/build-20260927-213244.log，Result: Succeeded。未启动编辑器或游戏测试。
