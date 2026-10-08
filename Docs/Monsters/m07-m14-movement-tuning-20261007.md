# 盲祷者、螺柱移动与转身调整

2026-10-07。用户认可 [M 系列移动排查](m-series-movement-audit-20261007.md) 建议后的实施记录。

| 对象 | 参数 | 原配置 | 本次配置 |
| --- | --- | ---: | ---: |
| 螺柱 M14 | 移速 | 56 cm/s | 112 cm/s |
| 螺柱 M14 | 导航/近敌转向 | 25°/s | 75°/s |
| 螺柱 M14 | 加速度 | 100 cm/s² | 200 cm/s² |
| 螺柱 M14 | 制动减速度 | 180 cm/s² | 360 cm/s² |
| 盲祷者 M07 | 慢走配置 | 63 cm/s | 82 cm/s |
| 盲祷者 M07 | 追击上限 | 129 cm/s | 168 cm/s |
| 盲祷者 M07 | 转向 | 180°/s | 180°/s |

M14 原生默认与正式蓝图同步更新。导航转向和近敌朝向修正共用移动组件的 RotationRate，每帧仅启用一种转向驱动，避免同一帧叠加。近敌朝向仍由服务器控制，攻击锁向和战斗时钟保持既有实现。

M14 动画源速保留 28 cm/s、25°/s，满速直行对应 4 倍、原地满速转向对应 3 倍播放。移动与左右转身切换时沿用循环相位，保留出场循环与姿势混合。螺柱此前扩大 25% 的旋转攻击范围保持当前配置。

M07 数值写入正式 BP，保留其当前 42/86 cm/s 的动画源速度及当前动作引用；不将旧原生默认动作和源速视为正式蓝图。本次只增加非反射选片函数，开始移动与持续移动共同使用以下阈值：

- 慢走 → 跑步：到 84 cm/s 时切换，避免继续停留在已达 2 倍播放上限的慢走片段。
- 跑步 → 慢走：降到 71.4 cm/s 以下时切回，保留 12.6 cm/s 的缓冲区。
- 继续沿用脚步相位映射和出场循环混合。新追击上限 168 / 源速 86 ≈ 1.953 倍，处于原有 2 倍上限内。
- M07 的慢走值是步态配置，移动组件实际追击上限为 168；本次不扩展或改变巡逻/返回行为。

运行时逻辑修改仅涉及 `BlindSupplicantMonster.h/.cpp` 和 `SpiralPillarM14.h/.cpp`。正式保存目标为 `/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07` 与 `/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14`。

后台入口 `Tools/MonsterAI/Complete-M07M14Movement20261007.ps1`，资产保存脚本 `Tools/MonsterAI/save_m07_m14_movement_20261007.py`。修改前快照位于 `SourceAssets/M07M14Movement20261007/Before/`，构建与资产保存回执位于 `Records/`。

Editor、Game 后台构建均已完成（退出码 0），两个正式蓝图均已通过 commandlet 保存。完成回执为 `SourceAssets/M07M14Movement20261007/Records/delivery.json`。未运行游戏测试、截图或渲染，实际移动和动画效果由用户测试。
