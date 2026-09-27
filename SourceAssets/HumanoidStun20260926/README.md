# 人形原地眩晕制作源

本机 `Dizzy` 来自 Mesh2Motion CC0 `human-addon-animations.glb`；原动作、目标体型拟合结果、许可和导入收据保留在本机。源码公开不包含目标网格或密集绑定/动作数据。

作者链：`Tools/HumanoidStun/export_source.py` → `retarget_source.py` → `Tools/HumanoidKnockdown/fit_recovery.py --root <本目录> --loop --plant-feet` → `Tools/HumanoidStun/import_fitted.py`。已完成的一次性 `complete_assets.ps1` / `end_play_for_import.py` 已移入 trash，不能把过去停止 PIE 的授权带进新的自动制作流程。

当前行为见 [眩晕](../../Docs/Monsters/humanoid-stun-20260926.md) 与 [硬直/眩晕分离](../../Docs/Monsters/stagger-stun-separation-20260926.md)。公开依赖及本机恢复边界见 [发布说明](../../Docs/Monsters/monster-hands-publication-20260927.md)。本次未重新运行游戏或验收。
