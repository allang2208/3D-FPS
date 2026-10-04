# 护冠双爪 V17：躯干发力与惯性回摆

用户反馈 V16 抓击缺少力度，并要求整体身体随攻击扭动。本次使用 V16 已修复的连续手臂模型，仅重做抓击动画的节奏与全身联动。

- 蓄力时胸腹反向拧转约 15°，挥抓时转至另一侧约 22°；转动分配到四节躯干，而非集中在一个关节。
- 躯干由后收转为前摆，带动小臂向前、向下内扣。主要挥抓压缩到约 0.395–0.49 秒，在收势位置短暂停留 0.03 秒，再以衰减回摆返回护冠姿态。
- 眼冠与六片背膜带少量延迟跟随，表现重量和惯性。
- 大支撑臂按固定抓握目标离线解算，保留原抓握位置和掌部朝向，继续复用运行时天花板 IK。

动画保持 1.10 秒、60 fps、67 个采样。命中区间仍为 0.35–0.55 秒；原 0.44 秒附近的挥抓音效与加速段对应。伤害、冷却、AI 距离选择和其他动作不修改。

制作脚本：`Tools/HangingBellM09/author_claw_body_drive_v17.py`。

制作源与导出：`SourceAssets/HangingBellM09Meshy20261003/ClawBodyDriveV17/Authoring/` 和 `Exports/`。

正式引用：`/Game/Monsters/HangingBellM09/V04/Animations/A_M09_Claw`。

导入保存由 `import_claw_body_drive_v17.py` 完成；无人界面入口为 `import_claw_body_drive_headless_v17.py`。实际状态见本轮 `Records/import_saved.json`。本次没有改网格、权重、骨架或物理资产，没有原生代码构建；未运行游戏测试或追加预览渲染，视觉表现由用户测试确认。

实际保存：2026-10-04 14:01（北京时间），后台导入脚本报告成功，正式 `A_M09_Claw.uasset` 已落盘，`import_saved.json` 为 `complete: true`。随后 commandlet 在退出清理阶段发生访问异常，调用栈包含 `URuneSwordComponent::~URuneSwordComponent()`，进程退出码为 1；不能将整个进程报告为正常退出。本轮未修改该组件，保存阶段与退出异常分别记录，未追加游戏测试。
