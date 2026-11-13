# 斩马刀改造、破军连斩与观峰镜

本批扩大赤霄红边，恢复赤霄、逐风作为专属符文的配色，并为斩马刀制作三类固定实例纹样。破军长柄沿用双手锤握姿，支持连斩和跃击。观峰镜的镜口覆盖、成像和远端变倍环也随本批保存。

## 恢复入口

| 内容 | 文件和恢复顺序 |
| --- | --- |
| 刀身、符文和旧档 | 工程根目录的 `Content/ColdSteelData/{melee-gunsmith,zhanmadao-modules,tang-dao-modules,whirlwind-temporal-materials}.json`。赤霄、逐风在 `blade_2`，实体刀身仍可独立选择。保留旧部件的颜色、ORM 和材质依赖。固定纹样种子在 `ModularSwordVisual` 生成，通过 `FPSBodyRuneVisual` 随世界装备重建。 |
| 唐刀和斩马刀表面 | 先恢复现有刀身和材质，再使用 `SourceAssets/DaoLongitudinal20261110` 的布局与材质配方、`ZhanmadaoDamascus20261111/ReferenceRefinementV3/patterns.py` 的三类纹场，以及 `Zhanmadao20261018/LegendaryRunesV1` 的专属装饰层。按当前配方依赖恢复。部分早期安装器只适用于历史阶段。 |
| 破军长柄 | `SourceAssets/Zhanmadao20261018/PojunLonghaft` 提供长柄制作、安装和配重接触点提取。根目录配置保留距离 ×1.5、物理伤害 ×1.1、体力消耗 ×1.25、攻速 ×0.75。刀身、重击和冲刺动作选择在 `Weapons/PojunGrip`。 |
| 连斩和砸地 | 原长柄双手握姿和标准剑轨迹是制作输入。恢复 `SourceAssets/ChainSlash20261107/Pojun/motion.json` 后使用同目录的 `save_asset.py` 保存专属动画。生产包路径为 `/Game/Skills/ChainSlash20261107/Animations/A_ChainSlash_Pojun`。地面环由 `SourceAssets/LeapStrike20261107/GroundWave/bake_wave.py` 与同目录 HLSL 生成，砸地音效包为 `/Game/Weapons/SteelWarhammer20261014/GroundImpactAudioV1/S_Warhammer_GroundImpact`。 |
| 观峰变倍镜 | 公开配置在 `bow-gunsmith.json` 的 `sight/highland_peakwatch_3_6x`。作者链见 `PeakwatchADSJoint20261110`、`PeakwatchCoverage20261110` 和 `SharedPhysicalOptics20261030/peakwatch_clear_lens.py`。恢复共用物理镜片后生成弓用清晰镜片，世界模型继续使用原玻璃。 |

## 共享源码

公开运行树包含可独立合入的物品配置、符文旧档迁移、纹样种子同步、第三人称双腕连续性、命中特效预载和物理镜片捕获。完整本机工程还含并行开发的锤、身体、弓与技能宿主。专属编译单元保存在 `Runtime/Source/FPSGAME`，恢复时按同名相对路径合并。共享宿主的本机散列、行号与实际代码见 [调用点](Integration/host-sections.json)，双腕拟合见 [动作代码](Integration/two-hand-body.json)。[带基线的补丁](Integration/baselines.json) 记录对应的旧快照和 LF 内容散列。按功能合并时，优先使用已有运行树的当前实现。

原双手剑连斩、动作时钟与资产约定见[技能动作前置](../SkillActions20261110/README.md)。观峰镜安装和先前的镜口覆盖见[观峰镜前置](../Conversation20261112/README.md)。动作、模型、UE 包、参考照片、声音、密集采样和编译产物由本机合法素材恢复。[本机资源清单](local-assets.json) 提供主要依赖的路径和散列。完整本机主工程已构建，本批未独立构建公开克隆。

## 已记录的检查

- 破军四刀在独立服务器、施放客户端和旁观客户端通过 80 毫秒延迟、2% 丢包检查，观测到四段双腕运动，首次冲击正常出现和消退。观峰镜的主客倍率环与重连在 60 毫秒延迟、5% 丢包下通过。重击砸地半径为双手锤 300 厘米、破军 450 厘米，两者都触发锤声。[联机记录](Evidence/network.json)
- 两款刀身与两款符文的四种组合都完成本地动作检查。材质组合包括斩马刀 378 组、唐刀 336 组；完整共享检查共 4,222 组，失败 0。28 帧观峰镜离屏采样包括 3 倍、6 倍和松弦。[动作](Evidence/pose.json) · [材质](Evidence/blade-finishes.json) · [光学采样](Evidence/optics.json)
- 尚待实机确认的项目包括各配重的独立联机快速近战命中、手腕与手指外观、快速转镜拖影、砸地听感与音画同步。四种刀身和符文组合未全部逐组重跑三端。上述记录来自先前测试，本次整理只做文件与发布检查。

11 个 V2 旧制作稿和临时链接文件已归档至 `trash/PojunPeakwatch20261113`。逐文件大小、SHA-256、替代物与原路径见[归档清单](archive.json)。
