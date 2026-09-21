# 大旋风 V5 作者源

当前运行资产的后摇已更新为 [RecoverV6](../RecoverV6/README.md)。本目录 Blend/FBX 保留为原 V5 制作基底，当前外送收势的可编辑源与接入记录位于 RecoverV6。

参考观察、动作设计、运行参数和接入状态见 [开发记录](../../../Docs/Skills/whirlwind-impact-v5-20260920.md)。

在 V4 连续蓄势和固定双手抓握基础上，强化横扫发力、第二圈连贯送出和收势制动。使用 `author_whirlwind.py` 生成普通柄可编辑 Blend 和 FBX，再经项目桥运行 `import_revision.py` 导入普通柄并制作加长柄。两个目标资产均为独立 V5，不覆盖 V4。

`whirlwind_motion.py` 为可修改关键姿态和曲线，运行阶段与 `Content/ColdSteelData/skills.json` 对齐；相机的 -720 度转身仅由运行时完成。`author_long_grip.py` 保留原普通柄动作家族，适配左手 18 毫米握距。

`Reference` 为用户指定第三方视频的本机观察资料，不是游戏素材，不公开分发。`Baseline` 仅保留本轮动手时相关共享源码的恢复快照，不用于覆盖后续并行修改。Manny、Blend、FBX、uasset 和密集骨骼数据保留在合法本机素材范围内。

本轮完成制作与必要接入，不主动测试、预览渲染或验收。
