# 冲刺攻击 V5：0.25 秒前摇

2026-09-21 按用户最新要求，在冲刺持剑与攻击之间加入 0.25 秒过渡，替代此前的瞬发入口。

- 源动画时钟从 `0.97` 秒开始，`1.22` 秒进入命中窗，播放倍率为 1。实际前摇为 0.25 秒，命中窗仍为源时间 `1.22–1.40` 秒，随后保留原下劈与收势至 `2.60` 秒。
- 标准柄和长柄分别制作 `SprintOverhead`。沿用 V4 右后高位持剑及低左肘；通过保持双手握点的整臂混合转入现有下劈，源时间 1.22 秒起保留原动作。任意步相或举剑中途点击，继续使用现有运行时姿态捕获交接。
- 前摇中没有命中、攻击挥砍音效或纵向裂隙；三者继续由同一接触时钟触发。镜头在前摇内渐入，避免直接跳到原下劈的蓄势镜头偏移。
- 满格后 0.5 秒举剑、冲刺循环与镜头步相、前方 60° 扇区和技能数值沿用现有实现。

作者源来自 `MeleeTacticalSprintReady20260921` 的参数、输入快照和骨架制作脚本；下劈源保持 `RuneSwordDowncutReach20260920` V5。这里只更新两条 `SprintOverhead`，其他六条冲刺动画仍使用 V4。

可编辑源：`Standard/Sword_DashWindup_Editable.blend`、`LongGrip/Sword_DashWindup_Editable.blend`。导入后各目录提供 `A_RuneSword_SprintOverhead.fbx`；UE 目标仍为各握柄 `TacticalSprint20260921/A_RuneSword_SprintOverhead`。

两种握柄的动画、FBX 已导入并保存，记录见 `import-02.txt` 与 `import_receipt.json`。首次导入在 PIE 状态保护处退出，没有写入；结束 PIE 后完成接入。

C++ 已通过 Live Coding 编译并应用于当前编辑器，记录见 `compile-live-01.txt`。本轮没有进行关闭编辑器后的常规基础 DLL 构建；源码已保留，后续常规构建会包含此次修改。未运行游戏测试、预览或验收渲染，效果交由用户测试。
