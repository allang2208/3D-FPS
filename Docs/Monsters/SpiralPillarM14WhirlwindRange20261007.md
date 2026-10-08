# 螺柱旋转攻击范围再扩大 25%

2026-10-07。在现有 V20 距离参数上乘以 1.25。

| 参数 | 调整前 | 调整后 |
| --- | ---: | ---: |
| 径向扫掠外端 | 162.5 cm | 203.125 cm |
| 扫掠球半径 | 36.4 cm | 45.5 cm |
| 判定外沿（未计目标胶囊） | 198.9 cm | 248.625 cm |
| 起手距离 | 247 cm | 308.75 cm |
| 追击停距（起手距离减 15 cm） | 232 cm | 293.75 cm |

原生接触范围位于 `Source/FPSGAME/Monsters/M14WhirlwindMotion.h`，原生起手默认值位于 `SpiralPillarM14.h`。正式蓝图 `/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14` 由 `Tools/SpiralPillarM14/import_whirlwind_range_20261007.py` 保存同一配置，既有选招和追击逻辑继续读取该属性。

旋转动画、攻击时序、伤害、击退和冷却沿用现有设置。场景遮挡与单次旋转每个目标只命中一次的逻辑保持不变。

后台制作入口：`Tools/SpiralPillarM14/Complete-WhirlwindRange20261007.ps1`，依次构建 Editor、Game，再通过无界面 commandlet 保存蓝图。修改前快照和实际完成回执位于 `SourceAssets/SpiralPillarM14Meshy20261004/WhirlwindRange20261007/`。

Editor、Game 后台构建均已完成（退出码 0），正式蓝图已通过 commandlet 保存；完成回执为上述目录的 `Records/delivery.json`。未运行游戏测试、截图或渲染，实际效果由用户测试。
