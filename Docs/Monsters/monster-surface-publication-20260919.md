# 怪物材质与僵尸犬发布整理

2026-09-19，用户接受本轮收尾，授权将废案归档、同步 SKILL 并普通推送到 `allang2208/3D-FPS` 的 `main`。本轮范围为狼派生僵尸犬、随机伤口 V5.1、胖子及手脑/毒蛆/突变体的材质统一；其他任务的并行修改保留在工作区。

## 当前入口与本机恢复

| 怪物 | 当前资源 | 保留的输入 |
|---|---|---|
| 野狼 | `Wolf/BP_WolfMonster`，既有动作数据集 | `QuadrupedTemplates`、`WolfMonster`，原 Animal Variety Pack 狼 |
| 僵尸犬 | `ZombieDog/V1/BP_ZombieDog` → `RefinedWoundsV5` 网格及动作数据集，V5.1 伤口参数 | V1 改造源与物理资产，FineSkinV3 作者源，RandomWoundsV4 分层贴图/网格/表面数据，RefinedWoundsV5 图集和毛层定位图 |
| 胖子 | `FatZombieMeshy/SK_FatZombie_Meshy` 的 `StyleV1/MI_FatZombie_Infected_V1` | 原 Meshy 源、`FatZombieStyleV1`，共享 `Monsters/Shared/InfectedSurfaceV1` 母材质 |
| 手脑 | `HandBrain/BP_HandBrain` → `StyleV1/SK_HandBrain_StyleV1` | `HandBrain20260910/surface_v07` 及现有解剖标记，`MonsterStyleV1/handbrain` |
| 毒蛆 | `PoisonMaggot/BP_PoisonMaggot` → `StyleV1/SK_PoisonMaggot_StyleV1` | 原 `PoisonMaggot20260911/delivery`，`MonsterStyleV1/maggot` |
| 突变体 | `Mutant3Meshy/SK_Mutant3_Meshy` 的 StyleV1 材质 | 原 `Mutant3Meshy20260915`，`MonsterStyleV1/mutant` |

表中 UE 相对路径均以 `/Game/Monsters/` 为根。所有角色继续使用原动画、攻击窗口、AI 与 F6 ID。源码发布包含尚未提交的狼/僵尸犬 F6 条目、独立显示名和伤口组件接入；突变体原生类及动作来源已在此前提交中发布，其 F6 条目与名称沿既有本机版本发布。

在合法本机素材完整的前提下：

1. 狼基础模板、跑姿与撕咬入口沿用 [狼](WolfMonster.md)、[跑姿](QuadrupedLocomotionV2.md)、[撕咬](WolfBiteV2.md) 的已有制作链。
2. 僵尸犬从 V1 → FineSkinV3 → RandomWoundsV4 → RefinedWoundsV5 恢复，当前安装脚本包含 V5.1 的 6～8 目标数量与放大的伤口图案。V5 首次 `ue_delivery.json` 保留历史 3～5 记录，后续状态以 `visibility_v51.json` 和当前安装脚本为准。
3. 胖子用 `Tools/FatZombie/author_style_sample.py`、`install_style_sample.py`、`activate_style_sample.py` 制作、导入并切换；已具备贴图时可跳过 Blender 制作。编辑器打开时使用对应 `.ps1` 完成实时接入。
4. 其余三只用 `Tools/MonsterStyle/author_surface.py -- handbrain|maggot|mutant` 烘焙，再用 `install_surfaces.py` 和 `activate_surfaces.py` 导入及接入。后两者在工程编辑器关闭时运行；只保存指定资产，不启动游戏。

原网格、原材质和合法输入保留。`MonsterStyleV1/previous_references.json` 是明确的回退引用，不能因版本较旧而当作废案。

## 归档

`trash/monster-surface-publication-20260919/` 保存已否决的无毛 V2：8 个作者文件、6 个 UE 包、3 份专用脚本；另有 2 份已被现有 `.blend` 替代的 Blender 保存备份。移动前已完成 Asset Registry 引用查询，V2 无外部硬/软/管理/可搜索引用。移动后按 SHA-256 读回。

具体原路径、归档路径、大小、散列、原因与替代物见 [19 文件清单](../AssetArchives/monster-surface-publication-20260919.json)。旧文档作为历史索引保留并标明新位置。V1/V3/V4 的有效依赖、当前源文件和回退材质没有移动。

## 发布与 SKILL

发布本次 C++ 接入片段、作者工具、HLSL、参数、来源、制作/接入记录及文档。个人怪物技能与工程镜像同步了 [感染材质规则](../../skills/ue5-monster-workflow/references/infected-surface-style.md) 和 [狼换皮经验](../../skills/ue5-monster-workflow/references/wolf-reskin.md)。

所有 Blend/FBX/uasset/贴图、第三方原始素材和密集骨骼/三角形数据仍留在本机。`geometry_layout.json` 与 `wound_surfaces.json` 为有效重建输入，此轮仅从 Git 跟踪中移除并精确忽略，不删除本地文件；原始历史未重写。合法使用来源沿用 `ZombieDogV1/CREDITS.md` 及 HandBrain 的现有素材 provenance，未重新认定皮肤包的公开再分发许可。

本次按授权完成仓库、暂存差异、大小、敏感信息和归档相关检查；不编译或运行游戏测试，不启动预览，不将既往制作完成记录改写为新的测试结果。
