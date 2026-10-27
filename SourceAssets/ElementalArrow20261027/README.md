# 元素箭图标与表现源

2026-10-27，内置 `image_gen.imagegen` 制作三枚图标。原始生成图完整保留于本目录，提示词见 `prompts.json`。

参考现用魔法箭雨图标：银色圆角金属框、石墨暗底、写实箭矢。火焰为橙红火舌，寒冰为蓝白寒气与冰晶，闪电为蓝紫电弧；无文字，框外透明。

- `elemental_arrow_fire.png`
- `elemental_arrow_ice.png`
- `elemental_arrow_lightning.png`

运行时 PNG：`Content/ColdSteelData/Skills/` 同名文件。恢复脚本：`Tools/Skills/restore_elemental_arrow_icons.py`。Texture2D 导入：`Tools/Skills/import_elemental_arrow_icons.py`，实际保存结果见 `Saved/ElementalArrow20261027/asset-receipt.json`。

特效直接引用现有 FlameArmor TorchV2 箭焰、IceSpike FrostV2 冰晶/寒雾/冰锥/碎裂、ElectrifiedMelee 箭身电弧、Lightning 连锁电弧、Fireball ImpactRealistic 爆炸与热冲击波。未覆盖原魔法或共享母版资产。

三图已生成并复制，2026-10-27 17:18 三份 Texture2D 后台导入保存完成；17:19 最终 Editor/Game 增量构建成功。保存回执为 `Saved/ElementalArrow20261027/asset-receipt.json`，构建回执为同目录 `build-final-receipt.json`。未运行游戏、视觉验收或重新打包。
