# 护冠双爪 V18：更快出爪与短促顿挫

用户要求抓击速度再快一些、打击感再强一些。沿用 V17 整身联动的制作方式，从 V16 连续手臂源重新烘焙 V18，避免在旧动作上重复叠加躯干旋转。

- 主挥抓由 V17 的 0.395–0.49 秒改为 0.38–0.445 秒，同一段手臂动作由 95 ms 压缩到 65 ms，时间缩短约 32%，该段平均播放速度约为原来的 1.46 倍。
- 蓄力更早完成；胸腹从反向约 18° 转向另一侧约 25.5°，下摆幅度约 11°，继续分配到四节躯干，带动双爪发力。
- 抓到底后的动作停留由 30 ms 改为 50 ms（0.445–0.495 秒）。这是动画内固定的收势顿挫，不是命中触发的全局时间暂停。
- 回摆加快，手臂约 0.98 秒回到护冠姿态；躯干、眼冠和膜片以衰减摆动收束。正式片段仍为 1.10 秒、60 fps。
- 大支撑臂按原抓握位置和掌面朝向解算，保留现有天花板 IK。原 0.35–0.55 秒命中窗口和约 0.44 秒挥抓音效继续对应挥抓阶段。

本次只替换正式动画 `/Game/Monsters/HangingBellM09/V04/Animations/A_M09_Claw`。保留修好的网格、权重、绑定和物理，未改伤害、冷却、AI、其他动作或原生代码。

制作脚本：`Tools/HangingBellM09/author_claw_snap_v18.py`。
导入脚本：`Tools/HangingBellM09/import_claw_snap_v18.py`；后台入口为 `import_claw_snap_headless_v18.py`。
源文件：`SourceAssets/HangingBellM09Meshy20261003/ClawSnapV18/Authoring/M09_Claw_Snap_V18.blend`。
导出：`SourceAssets/HangingBellM09Meshy20261003/ClawSnapV18/Exports/A_M09_CrownClaw_Snap_V18.fbx`。
保存收据：同目录 `Records/import_saved.json`。

制作与导出已完成，正式资产保存状态以保存收据为准。未启动游戏测试、预览或渲染，由用户体验确认。

实际交付：2026-10-04 14:55（北京时间），后台导入收据 complete=true，正式 A_M09_Claw 已保存；commandlet 正常退出，退出码为 0。未运行游戏测试或渲染。
