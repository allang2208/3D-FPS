# 陨石撞击可见性修复

用户反馈 Reference V7 几乎没有改善，因此 V7 仍未通过用户观感确认。本次针对当前运行引用排查，继续保留岩体、已有碎块、V6 包覆火焰/尾迹、V4 低矮残火及玩法数值。

## 已定位的源帧错误

当前 Impact 路径为 `MeteorImpactReferenceV7/NS_MeteorPressureV7`。用户此次编辑器启动晚于上次 Game/Editor 构建完成，日志也出现 V7 系统及图集，因此不能把问题简单归因于旧进程未更新。

`T_MeteorPressureFieldsV7` 是火焰、热量和烟共用的 64 帧数据图集。对实际 PNG 逐帧读取：R 通道的明显火焰只在第 0–9 帧；第 10 帧最大值仅 1/255，第 11 帧起为零。B 通道的烟仍持续到后段。

旧火冠把 `(.045 + .70 * NormalizedAge^.82) * 63` 当作火焰帧号。虽然粒子寿命设置为 0.82 秒，但它在约 **0.0744 秒**就抵达第 9 帧，随后越过火焰有效区。继续增加图集后半段的亮度不能恢复已为零的火焰覆盖率。这是本次直接定位到的可见性缺陷，之前“0.82 秒完整火冠”的描述只反映粒子寿命，未反映有效燃烧时长。

依据保存在 `SourceAssets/MeteorVisibilityRepair20261114/source-frame-diagnosis.json`。此次运行日志还记录过 V7 渲染准备超时，约 140.8 秒后完成编译；这可能影响尚未就绪时的首次播放，不能据此解释其后每次观感，也不据此改动整个技能准备系统。

实际资产报告 `loaded-assets-before.json` 中，9 个 Renderer 的动态材质参数均绑定到存在的 `Particles.DynamicMaterialParameter`，不是动态参数缺失。另一方面，3 个使用 CustomAlignment 的冲击波/火星 Renderer 仍绑定到已经不存在的 `Particles.ShapeLocation.ShapeVector`，未读取脚本写入的 `Particles.SpriteAlignment`；UV 绑定也仍读取模板的 `Particles.UVScale`，而脚本写入的是 `Particles.SpriteUVScale`。这些继承绑定在本轮改为显式绑定当前写入的属性，避免模板默认值覆盖制作意图。

## 修改

- 图集契约新增独立 `playback_windows`：火焰为 0–9.65，烟为 0–63；导出器从实际燃烧覆盖生成火焰窗口。
- 白热核心和 0.82 秒火冠各自在火焰窗口内播放，保留原有温度、覆盖衰减及曝光补偿。
- 接触亮芯从 85 ms 延长到 140 ms；核心粒子从 220 ms 延长到 260 ms。
- 径向冲击从 200 ms 延长到 320 ms，改为地面起始的上半扇面。原本以贴近地面的中心向上下对称扩张，向下部分会被地形遮挡；现在形状原点和 Renderer Pivot 同为 V=0.90。
- 直接更新原运行资产，保留原引用、Cook 路径、粒子数量、烟预算和灯光数量。无需原生代码构建。
- 冲击系统 Renderer 显式绑定 `Particles.SpriteAlignment` 和 `Particles.SpriteUVScale`；火星按飞散方向拉伸，图集按已写入的 UV 缩放采样。

## 交付边界

制作入口为 `Tools/Skills/repair_meteor_visibility_20261114.py`；完整重建入口 `build_meteor_reference_v7.py` 同步保留修复，避免重建恢复错误帧映射。局部修改前的资产保存在本轮目录 `Before`。

帧段/扇面实际保存以本轮 `repair-receipt.json` 为准，对应批次为 `inspect-process.json`；后续绑定修改看 `binding-repair-receipt.json` 和 `bindings-process.json`。只做用户要求的针对性排查与资产制作，不启动交互 UE、游戏、PIE、截图或视觉验收。用户自行查看修复后效果，未声称与视频 100% 一致。

2026-11-14 17:13 后台批次全部完成，两个进程均返回 0。当前 V7 系统、放射扇面材质及图集元数据已保存；9 个 Renderer 的方向、UV 和动态材质绑定在保存回执中均指向存在的属性。Niagara 编译回执为 `valid=1, pending_after=0`，`MeteorAssets.h` 的 Impact 仍指向同一 V7 系统。最终汇总为本轮 `delivery.json`，没有进行游戏或视觉验收。
