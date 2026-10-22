# 陨星范围与模型放大（2026-10-19）

用户要求陨石模型放大并匹配影响范围，作用范围变为当前 3 倍。本次按技能现有半径字段执行：爆炸和后续熔火的半径、每级半径成长均乘 3。不是面积乘 3，也没有将施法射程一起放大。

| 项目 | 原 1 级 | 新 1 级 | 原 20 级 | 新 20 级 |
|---|---:|---:|---:|---:|
| 爆炸半径 | 2.175 m | 6.525 m | 3.60 m | 10.80 m |
| 熔火半径 | 1.86 m | 5.58 m | 3.00 m | 9.00 m |
| 陨石模型最长边 | 0.80 m | 2.40 m | 0.80 m | 约 3.97 m |

`Content/ColdSteelData/skills.json` 的陨星字段改为 radiusBase=420、radiusPerLevel=15、auraRadiusBase=360、auraRadiusPerLevel=12；原 unitsToCM=1.5 保持。

## 视觉与作用范围

- 原 `FireMagicStats` 公式仍产生施法快照；技能详情、长按预览圈、权威爆炸／熔火查询、玻璃破坏、草地冲击、水火交互及远端复制均继续消费该快照中的半径。
- `FPSMeteorStrike.cpp` 用爆炸半径相对原 1 级 217.5 cm 的比例驱动岩体最大尺寸、包覆火焰、尾焰宽度与精灵尺寸、触地中心偏移和碎片尺寸／散布。保留 12 块碎片及原消失时序。
- 熔火用实际 AuraRadius 定位；火焰精灵按 AuraRadius / 186 cm 调整尺寸，保留原粒子数量并扩大运行时包围盒，避免新范围超出旧 650 cm 包围盒被裁剪。
- 爆炸效果继续按 Radius 缩放，冲击波与预览圈同源。陨星局部空间余烟的 User.ImpactGrowth 归零，由组件统一缩放，避免烟片再乘一次 Radius 比例而膨胀到范围外。
- 包覆火焰是局部空间粒子，使用组件缩放；尾焰是世界空间粒子，增加 User.VisualScale 调整其喷出横向偏移和 SpriteSize，不把真实飞行轨迹整体缩放。
- `install_vfx.py` 仅增量修改 `NS_MeteorNaturalWake` 和 `NS_MeteorNaturalAfterfire` 中目标赋值表达式，保留已有发射器、材质和附加层。`Tools/Skills/build_fire_magic_realistic.py` 同步修改重建配方。
- 伤害、蓝耗、冷却、持续时间、0.65 秒坠落、13.2 m 固定出生高度，以及地层／遮挡规则保持现有值。

## 产物

源码与原资产备份位于 `SourceAssets/MeteorRange3x20261019/Before/`。

- 尾焰、熔火两份 Niagara 系统最终编译并保存成功，后台 commandlet 退出码 0；回执 `SourceAssets/MeteorRange3x20261019/install-receipt.json`（complete=true），最终日志 `Saved/MeteorRange3x20261019/install-commandlet-02.log`。
- `FPSGAMEEditor Win64 Development`：Succeeded，退出码 0，8.58 秒；目标已为最新，无需重复编译，日志 `Saved/MeteorRange3x20261019/FPSGAMEEditor-build-01.log`。
- `FPSGAME Win64 Development`：Succeeded，退出码 0，7.07 秒；目标已为最新，无需重复编译，日志 `Saved/MeteorRange3x20261019/FPSGAME-build-01.log`。
- 构建回执：`SourceAssets/MeteorRange3x20261019/build-receipt.json`。

未运行游戏、视觉预览或联机测试；模型、火焰比例及实际范围体验由用户确认。

整理说明（2026-10-22）：本页保留阶段记录；Before 备份和已替代作者的归档位置、当前资源及公开恢复边界见 [陨星发布记录](../Publication/Meteor20261022/README.md)。
