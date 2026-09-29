# 普攻 V28：整臂驱动

按用户对 V27 的否定反馈，重做肩、上臂与肘部驱动，并让手和长杖由同一骨段链带动。允许后撤出屏，稳定腕部抓握，保留非线性动作、冲量及命中顿帧。

`author_motion.py` 已生成四种握柄 × 五个完整关键姿态；`save_editable.py` 已由后台 Blender 5.1.2 执行并保存 `Staff_PrimarySmash_V28.blend`。本目录 `full-pose.json`、`editable-source.json` 与运行头是同源交付。

完整说明见 [开发记录](../../../Docs/Weapons/staff-primary-whole-arm-20260928.md)。常规 Editor 构建已成功并更新基础 DLL，日志 `Saved/BuildEditor/staff-whole-arm-v28-20260928-105154.log`，回执 `build-receipt.json`；没有新 UE 动画包需要导入。未启动 UE、游戏或进行测试／渲染。
