# 2011 制作源整理、废案归档与发布

2026-10-03。按用户授权整理本对话的 2011 制作链、更新技能和发布源码。整理不启动 UE、不重新制作资源、不运行游戏测试；已有制作、导入及构建回执只记录当时事实。

## 当前制作链

| 部分 | 当前源与保存范围 |
| --- | --- |
| 原枪、原生手模与动作 | `SourceAssets/PitViper2011Integration20261002`；canonical_parts、原始 Blender 与 Single/Dual 源均保留本机 |
| 开火表现 | `PitViper2011Fire20261002`；八条更新后的开火序列已回写主制作记录，完整动作和源文件保留 |
| 普通及共用消音声 | `PitViper2011FireAudio20261002`；普通声为用户指定 M2011viper，共用消音声沿既有手枪路径；当前响度参考在 `Inputs/SuppressedLoudnessReference_float.wav` |
| 通用配件和三款瞄具座 | `PitViper2011Attachments20261002` → `PitViper2011OpticPreviewFix20261002`；三款旧瞄具 Blender 仍是新安装座的必要光学主体输入，保留 |
| SI 枪口补偿器 | `PitViper2011SICompensator20261002/author_si_compensator.py` 与 `PitViper2011SIBodyExtension20261003`，接口用 `Tools/Weapons/pit_viper_si_extension.py`；当前完整原生枪口延展模型与分区恢复输入保留 |
| 私有细腻表面 | `PitViper2011SurfaceRefine20261003`，保留输入快照、母版映射和三款通用防滑纹图；VIP 图从当前长覆片源取用 |
| VIP 蝮蛇防滑纹 | `PitViper2011ViperLongitudinalGrip20261003`，两侧纵向覆片、斜向底缝与专属图标已实际保存 |
| 三款通用防滑纹 | `PitViper2011CommonLongitudinalGrips20261003`，共用原 GripSurface 路径，物理 UV 保持纹理密度；已实际保存 |

VIP 和三款通用纹理的覆片仅在握把本体两侧，沿斜向下沿裁切并留出间距，不覆盖弹匣、底板、扩口和卡扣。旧 GripRebuild 入口只转发当前两套制作源，附件全套作者不再先生成旧短覆片。旧图标单独导入入口也指向当前图标。

SI 属性保持用户设定：开镜耗时 −10%、后坐力 −10%、稳定性 +5%、腰射随机散布 −20%；VIP 蝮蛇防滑纹腰射随机散布 −15%。通用纹理属性保持现有目录值。

## 废案与恢复依赖

200 份文件、1,768,416,722 字节已移动到 `trash/pit-viper2011-closeout-20261003`，没有删除。包括旧短覆片及其图标/贴图、已被原生枪口延展替代的上肩 SIChamfer 方案、旧音频处理版本、历史诊断和回退快照。逐项记录原路径、目标、大小、SHA-256、原因、替代物及相同散列读回，见 `SourceAssets/PitViper2011Publication20261003/archive-manifest.json`。

当前原生几何、骨架源、活动动画家族、光学供体、声音输入/母带、材质输入快照、正式 UE 包及当前制作回执保留原生产位置，不按旧日期归档。仍有用的响度参考移入当前 Inputs；SI 延展制作读取当前 SI 作者记录，不再依赖被归档的 Before 快照。

旧图标记录和旧 README 中的导出列表是历史说明；恢复时以上表及当前 authoring/import_receipt 为准。归档物用于回滚，不应执行其旧导入脚本覆盖当前资产。

## 公开范围与依赖

公开原创程序制作/导入/目录脚本、说明、归档元数据、对应技能、2011 配件与防滑纹的相关原生接口及精确目录修改。共享文件只提交本任务片段，保留工作区其他未提交内容；具体清单见 `published-files.json`。

本机保存的 Sketchfab 模型元数据标注 CC Attribution 4.0，作者 D_U，要求署名且允许商用。模型源为 [Low Poly TTI JW4 Pit Viper 2011](https://sketchfab.com/3d-models/low-poly-tti-jw4-pit-viper-2011-2daaf7fe78604ee7941a4ad5fd4d0153)。此公开提交按项目规则保留署名与制作配方，不上传原始模型、派生高密度几何、UE/Blender/FBX/OBJ 包、贴图、参考图、字体、密集姿态、缓存、日志或音频。

Epic/Manny、V7 手模、M1911/G18/通用配件、WS 材质母版和声音权利仍按各本机输入许可恢复；用户音频的再分发未核准，仅留本机。Git checkout 不是完整可运行资产包，恢复所需输入与当前资产路径见 `retained-recovery-dependencies.json`。

仓库整理检查包括归档路径/散列读回、精确暂存差异、空白错误、文件大小/敏感信息、来源边界、远端分支与待推送提交；这些检查不等于游戏测试、打包或视觉验收。
