# 突变体-3：当前版本、恢复与源码发布

整理日期：2026-09-23。用户确认表面修订“成功了”，飞扑距离与提前量“基本成功”，随后授权归档废案、沉淀技能并推送。本页是当前入口；同日各阶段文档保留当时事实，不把第一版参数当作现行配置。

## 当前结果

- 成熟 Khaimera 身体动作与 Meshy 外观结合：快速奔跑、两段爪击连击、蓄力/真实飞行/落地恢复；30 根新增指骨形成外展内钩的爪型。
- 原身体统一时间重排后，只给腾空和落地片段叠加腕/指旋转，双爪向下挥击。独立肘部/手腕求解版本已退役。
- 追踪使用保留距离与记忆，突变体有有效目标时不因出生点距离往返；堵路重规划、攻击可达位置及实际速度待机避免卡死/慢动作。
- 最大飞扑选择距离 1125 cm，比原 750 cm 增加 50%；0.65 s 飞行中预测目标水平移动，最多 450 cm，起跳重算。预测受墙体、距离、可走地面、高差和胶囊轨迹约束，失败退回较小提前量或追击。
- 真实落地前方 120°/250 cm 扇形判定；伤害为基础攻击 3 倍，成功伤害后存活玩家眩晕 2 s。保留弹反打断、死亡取消与输入锁释放。
- 贴地冲击波、尘土、短砸地声和命中相机反馈使用现有有容量上限的特效系统。
- 当前单槽网格修复 section 绑定；保留表面实例、身体法线基础并局部修正指爪法线，近景短期保留指定纹理 mip。

## 本机资产和许可边界

本次 Git 发布代码、作者配方、文档与归档清单，不公开用户参考照片、模型、贴图、声音、FBX、Blend、uasset、密集动作采样或制作工程缓存。商业使用权不等于原始资产再分发权；完整本机内容恢复仍需要合法素材备份。

| 依赖 | 本机恢复范围 |
| --- | --- |
| 现行主体 | `Content/Monsters/Mutant3Meshy/KhaimeraV2`：SK_Mutant3_Claw、其 Skeleton、9 段 Animations、相关物理引用 |
| 原身体/战斗 | `Content/Monsters/Mutant3Meshy` 的原模型、物理、Death/Stagger 及其骨架；`Content/Monsters/AI` 行为树/控制器 |
| 当前表面 | `Mutant3Meshy/SurfacePolish` 的 MI 和四张专用贴图；仍需 `StyleV1` 及 `Monsters/Shared/InfectedSurfaceV1` 共享父材质依赖 |
| 落地反馈 | `Mutant3Meshy/Effects/{M_Mutant3LandingWave,S_Mutant3PounceImpact}`；现有 GunplayFX impact 池资产、原 HandBrain slam 声音及其来源许可 |
| Fab 纹理 | 用户已有 `Content/Vefects/Easy_Impact_Frames` 中冲击波材质引用的 Noise Texture/Intensity Mask；[来源](https://www.fab.com/listings/15cb7c95-3220-43fe-8d68-c67c73e83eba) |
| 动作来源 | 用户已下载 [Epic Paragon Khaimera](https://www.fab.com/listings/e7c665c1-8c13-42f0-9152-0753008853d7)，原包保留在 VaultCache/后台 UEAuthoring；不是开源/CC0 |
| 身体与历史动作 | 用户 Meshy 模型的独立授权；原 `Mutant3Meshy20260915/godot_runner/Mutant3_Meshy_CombatBase.blend` 是保留输入，Denys 旧动作署名不因更换奔跑而删除 |

没有新下载或上传第三方二进制；本次没有重新做网页许可证调查。当前采用依据沿用前序本机来源记录，公开范围保持为自编代码/制作方法。

## 从合法本机备份恢复

不默认执行以下制作步骤。现有 Content 已落盘；普通继续开发直接使用当前资产。重新制作时先具备上表素材，按源依赖恢复，不在运行中的编辑器覆盖未保存内容。

1. `SourceAssets/Mutant3Khaimera20260923/retarget_khaimera.py` 与 `author_feral.py` 保留原生重定向及干净身体动作；需要原包、`native_retarget`、元数据及 CombatBase。`UEAuthoring` 是本地素材制作宿主，不是第二份 C++ 开发真源。
2. `hand_ground_fix/author_claw_skin.py`、`author_fixed.py` 和 `inspect_fingers.py` 保留手指区域输入、接地动作与可编辑源；虽然后续爪型替换了旧外形，此层仍是重建依赖。`finger_components.json`、`claw_skin.json`、合同和 Blend 均留在本机。旧 `import_fixed.py` 只用于早期制作层，不是最终安装入口。
3. `claw_reference_20260923/author_open_claw.py`、`import_open_claw.py` 生成当前张开爪型骨架/权重及基础动画；导入网格时保留当前材质和作者法线。
4. `pounce_arm_refine/author_reference_rake.py`、`import_reference_rake.py` 重排完整身体姿势；再执行 `pounce_impact_20260923/author_downward_hands.py`、`install_downward_hands.py`，仅将腕/指旋转写入两段正式动画。**最后不能再用旧完整 FBX 覆盖手部补丁。**
5. `transitions/inspect_transitions.py` 和 `build_gait_map.py` 仅在更换循环片段、且获准重采样时生成相位映射；密集 `clip_poses.json` 留本机，运行只用 C++ 索引表。
6. `SourceAssets/Mutant3SurfacePolish20260923/author_normals.py`、`install_surface.py` 安装局部法线、SurfacePolish 四贴图和 MI。不要把旧 `texture_fix` 基础材质重新赋给当前网格。`material_return_fix/repair_surface.py` 是 section 修复入口。
7. `SourceAssets/Mutant3LandingFX20260923/author_assets.py` 从上述已有纹理/音源生成专用反馈资产。原生 `RepairSurfaceBinding` / `ApplyPounceHandTracks` 需先编译当前模块。

源文件、阶段安装脚本与最终安装顺序都保留；制作日志/回执用于本机追溯，不代表在新 checkout 已安装资产。

## 废案归档

76 份文件已移入 `trash/mutant3-feral-20260923`，逐文件原路径、目标、字节数、SHA-256、原因和替代入口见 [归档清单](../AssetArchives/mutant3-feral-20260923.json)。包括 `pounce_downclaw`、`author_arm_only_attempt.py`、其历史对照工具，以及本轮被替代的源码/资产快照和 Blend 自动备份。移动后已读回散列。

旧文档里的 before/baseline 路径是当时记录；现在在归档根下按原相对路径取回。恢复必须逐文件确认，不将整个旧快照覆盖当前工程。当前运行 Content、原始许可素材、干净重定向、接地源、当前可编辑源未移入 trash；不凭目录名称“final”或旧日期认定废弃。

## 发布与交付边界

从独立仓库 `D:/FPS3D/FPSGAME` 发布至 `https://github.com/allang2208/3D-FPS.git` 的 `main`。遵循 WORKFLOW 第 8 节：fetch、审查待推历史、精确暂存、检查暂存差异/空白/大小/敏感信息/素材范围，普通 `HEAD:main` 推送后回读远端。

共享源码纳入突变体所需的 AI 分派、脚底导航坐标/同层停步前置修正、动画过渡、落地特效组和 Editor mesh 模块。受击片段与控制时钟实现是当前突变体已有调用的前置依赖；保留动画实例的旧单参数受击接口，使已发布的旧调用与当前显式片段接口均可使用，该兼容入口不改变当前宿主的调用。角色等级/韧性重构、其他怪物业务、地牢 Boss 锁定及通用导航目标投影策略、枪械命中音与其他并行功能未纳入本次提交。

已完成的历史 Editor 构建：`Saved/BuildEditor/build-20260923-234049.log`；已保存材质/动画/特效的具体记录见各阶段文档。这个构建针对当时完整宿主，不等于本次拆分发布树重新编译。此次整理仅做授权的归档与推送检查，未启动 UE、游戏、自测或重新渲染；由用户继续测试。
