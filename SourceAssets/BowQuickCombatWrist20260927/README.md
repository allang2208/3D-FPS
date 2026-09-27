> 2026-09-27 整理：此版被 V7 替代。旧 `Export/` 已移到 `trash/melee-bow-iterations-20260927/SourceAssets/BowQuickCombatWrist20260927/Export/`；作者脚本、Blend、接触拟合及回退备份仍保留。历史导入脚本的旧导出路径不再是当前重导入口。当前版本与恢复边界见 [发布记录](../../Docs/Weapons/melee-bow-publication-20260927.md)。

# 弓快速近战 V6：左腕自然延伸

2026-09-27，按用户要求减轻左腕上拱，让前臂自然延续原握姿。

沿用 V5 的完整左掌和手指世界姿态，不移动握点。将前臂朝握姿对应的中性方向调整，保留约 12° 的骨架轴线折角；肘部相应抬起，肩部按原生上臂长度做最短位移支撑。12° 是此动作的制作参数，不是人体医学角度或视觉验收结论。辅助骨完整跟随所属骨段，骨长、缩放和蒙皮保持。

修正随抬弓平滑进入，收势平滑交回原待机。保留 V5 右手张掌、弓的水平前推轨迹、击中时点和运行时加速/镜头反馈。

- `author_wrist.py`：作者脚本，依赖保留的 `BowQuickCombatPalm20260927` V5 源。
- `Bow_QuickCombat.blend`：可编辑骨架与新动作。
- `Export/A_Bow_QuickCombat.fbx`：240 Hz 烘焙动画。
- `import_wrist.py`：原路径替换、压缩与保存，执行写入前将旧 V5 二进制备份到 `Before/`。
- 正式资产：`/Game/Weapons/DarkBow20260925/QuickCombat20260926/A_Bow_QuickCombat`。
- `import-receipt.json`：成功导入保存后生成的回执。

已通过当前编辑器的 MCP 互斥批次完成导入、压缩与保存，回执见 `import-receipt.json`；旧 V5 二进制已备份到 `Before/`。此前被 PIE 阻止的两个批次未修改资产，本次继续后完成正式接入。

本轮只制作、导出和接入；未进行渲染、额外动画检查或游戏测试，由用户确认腕部轮廓与手感。
