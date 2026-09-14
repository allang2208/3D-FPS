# Gunplay V8：浓白烟与柔化火光

后续手枪火光尺寸与连续烟雾改造见 [V9 交付记录](gunplay-vfx-v9-20260914.md)。V8 步枪火光作为保留基准和重建依赖。

按用户对 V7 的反馈继续精修：保留当前烟火方向，进一步增加烟雾浓度并改为白烟；火光外缘采用连续渐变，延长淡出。

## 已接入的修改

- 烟色从线性 RGB `(0.58, 0.60, 0.62)` 改为偏冷白 `(0.92, 0.94, 0.96)`。默认烟雾透明度从 `0.60` 提高到 `0.72`，普通每发烟为 `0.864`、LPVO 为 `0.828`，保留独立的消音器烟雾尺寸。
- 喷烟材质不透明度增益为 `1.95`，余烟为 `2.15`。材质使用粒子颜色作为底色，关闭黑体染色和按粒子透明度裁轮廓的分支；保留纹理内的明暗层次。
- 每发烟寿命改为 `0.75–1.05 s`，余烟为 `1.00–1.35 s`。烟团在前 6% 寿命内形成，34% 之后逐渐散去。余烟热量透明度乘数从 `1.10` 提高到 `1.25`。
- 火光新增独立项目母材质 `M_MuzzleFlashFeatherV8`。直接读取原贴图蒙版，柔化灰度边缘，再乘粒子透明度，绕过原裁切和阈值侵蚀路径。保留原母材质最后的预乘合成，使发光与透明度共同淡出，避免只剩亮轮廓。
- 保留亮芯与焰瓣的不同层次：亮芯 `40–60 ms`，前焰 `95–125 ms`，侧焰 `70–100 ms`。透明度采用短起势和缓慢末段消退，V7 的随机角度、随机焰瓣与尺寸变化继续保留。
- 火光材质不透明度增益为亮芯 `0.90`、焰瓣 `0.82`；运行 HDR 亮度乘数稍降到普通 `0.80`、LPVO `0.90`。保持可见火光，同时降低清晰的剪影感。
- 曳光、枪身抛壳点和 LPVO 1–6x 隐藏弹壳规则沿用当前实现。

## 作者源与依赖

- `Tools/AssetPipeline/build_gunplay_presentation_v8.py`：从 V7 与合法本机 Epic 母材质生成 V8。
- 历史一次性读取器 `read_gunplay_flash_material_source.py` 用于读取本机 V7 火光材质节点与参数，现已归档到 `trash/gunplay-20260914/Tools/AssetPipeline`；V8–V10 的正式制作器和输入仍保留。
- `Source/FPSGAME/Weapons/FPSWeaponFXComponent.h/.cpp`：颜色、密度与系统引用。
- 七项新资产均位于 `/Game/Weapons/GunplayFX/`：`M_MuzzleFlashFeatherV8`、`MI_MuzzleFlashCoreV8`、`MI_MuzzleFlashLobesV8`、`MI_MuzzleWhiteV8`、`MI_BarrelWhiteV8`、`NS_FPS_MuzzleEpicV8`、`NS_FPS_BarrelSmokeEpicV8`。

恢复顺序为 Epic NiagaraExamples → V5 → V6 → V7 → V8。原始及派生二进制继续作为本机授权依赖保存；没有改写 Epic 原包，没有新增第三方代码。

按用户全局规则，本轮不运行游戏、自测、截图或视觉验收；实际白烟浓度与火光淡出观感由用户测试。

资产制作记录：`Saved/Logs/GunplayV8-Assets-20260914-a.log`，七项资产保存完成，两套 Niagara 编译完成；生成清单为 `Saved/GunplayVFX20260914/created-assets-v8.json`。Python 制作成功；Commandlet 整体退出码为 1，来自项目已有的 GameFeatureData 资产管理配置错误，没有改动该无关配置。

原生构建完成：`Saved/BuildEditor/build-20260914-002730.log`，`Result: Succeeded`。工程构建脚本生成普通 `UnrealEditor-FPSGAME.dll` 及依赖模块；没有启动游戏测试。
