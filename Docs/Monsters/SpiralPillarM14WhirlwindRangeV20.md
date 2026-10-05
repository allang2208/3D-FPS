# 螺柱 M-14：旋风范围增加 30%

> 此为该阶段的制作记录。当前版本、归档位置与恢复依赖见 [整理发布](SpiralPillarM14Publication20261005.md)；不将中间方案视为当前安装入口。

2026-10-05。按用户要求将旋转攻击的距离参数乘以 1.3。

| 参数 | 原值 | 新值 |
| --- | ---: | ---: |
| 径向扫掠外端 | 125 cm | 162.5 cm |
| 扫掠球半径 | 28 cm | 36.4 cm |
| 判定外沿（未计目标胶囊） | 153 cm | 198.9 cm |
| 起手距离 | 190 cm | 247 cm |

追击停距继续使用起手距离减 15 cm，随配置变为 232 cm。六圈旋转的动作与时序、物理伤害倍率、击退距离和 12 秒冷却保留。

修改位于 `M14WhirlwindMotion.h` 和 `SpiralPillarM14.h`。Game 和 Editor 目标均已后台构建，退出码 0；正式蓝图已保存 247 cm 起手距离，与新的原生命中范围一致。

2026-10-05 通过无界面 commandlet 执行 `import_death_and_range_v20.py`，顺序完成 V19 死亡修复和 V20 范围配置的导入保存，退出码 0。源清单当前版本为 ProductionV20；资产保存回执见 `ProductionV20/Records/ue_revision.json`。

未打开 UE 图形编辑器、未运行游戏测试或渲染，交由用户测试。`ProductionV20/Records/pending.json` 已标记接入完成。
