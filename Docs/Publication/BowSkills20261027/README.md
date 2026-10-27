# 弓系技能整理与发布

本批整理 2026-10-26/27 的穿心箭、魔法箭雨、元素箭、照明箭、节拍显示、修炼详情，以及最后一轮持续拉弓资源和队友搭箭表现的联机修复。当前本机完整工程仍为 `D:/FPS3D/FPSGAME`。

## 发布范围

- `patches/` 保存 98 个经过归属裁剪的源码/配置增量，包括新增技能组件、箭体/空爆/标记、轮盘/卡片、权威资源与取消路径，以及隔离检查夹具。公共宿主已有未发布的库存、身体、魔法和武器前置，故这些补丁作为明确的集成材料保存，不把其他开发一起覆盖进公共运行树。
- `skill-definitions.json` 保存四项技能的当前精确配置键；合入 `Content/ColdSteelData/skills.json` 时只合并这四个键，不覆盖其他技能。魔法箭雨使用独立敏捷/智力 2:1 系数；元素箭最终火焰 2.75、冰/电 2.50，射出费用 ×1.5，实际拉弓 3 MP/s。
- `Tools/Skills/` 保留当前箭雨 V2→V3→V4 资产制作链、元素图标恢复/导入、照明材质/图标制作。`SourceAssets/` 公开原创配方、提示词、着色器和音源署名记录；当前生成 PNG、声音、模型与 UE 包保留本机。
- 技能、武器、联机存档三处 SKILL 统一链接到 [弓系准备技能](../../../skills/ue5-skill-magic-workflow/references/bow-prepared-skills.md)，个人维护源和工程镜像同步。

## 增量恢复合同

[integration-manifest.json](integration-manifest.json) 记录目标、补丁、前置来源、规范化基线/结果 SHA-256 和完整本机源 SHA-256。规范化为 UTF-8 去 BOM、CRLF 转 LF。`HEAD` 基线为清单中的 `head_reference`；`SourceAssets/.../Before` 基线现位于归档清单对应的 trash 位置。

档案合并补丁的前置由完整当前文件移除本批弓改动而构造，明确保留既有库存/影子档框架；清单标注为 reconstructed prerequisite。不得将该基线误称历史 Git 提交。98 份补丁均能对各自所记前置重建所记结果，但这些前置并不全包含在公共 HEAD 中；本次没有对干净克隆构建。

恢复需先准备 `CommitCampfireState`/库存回执与版本、权威影子档、当前弓与穿心箭基础、`PlayerSkillAssets` 后台准备、共用法术和遮挡/怪物命中框架，再按前置核对合入。涉及枚举、USTRUCT 和 RPC 的两端必须使用同版二进制。`SourceAssets/MagicArrowRain20261026/Before` 已含当时的穿心箭与节拍基础，不能把针对它的后续增量盲套到更早公共文件。不能用任何裁剪结果覆盖当前本机共享源文件。

与弓改造山鸣弦、火甲箭附焰、可变倍镜、近战配件、食品/焚化/木工及其他并行功能交织的差分没有整文件发布；它们仍在原工作区和原暂存区。补丁的前置依赖与本批直接拥有的代码应分别恢复。

## 资产与声音

关键 Cook 目录为 `/Game/Skills/HeartPiercingArrow/Audio20261026`、`/Game/Skills/MagicArrowRain20261026`、`/Game/Skills/IlluminationArrow20261027`。元素箭复用原火球、冰锥、雷电和火甲资源；具体软引用见 [asset-dependencies.json](asset-dependencies.json)。该清单不是所有传递资产依赖的完整导出。

箭雨基础作者会顺序调用 AirburstV2、ConeV3 和 VisibilityV4；三个升级脚本仍是有效输入，不按版本号归档。声音当前作者链为 `StrongV2/author_strong_candidates.py` → `BalancedV4/rebalance_efg.py` → `SelectedH` → `import_audio.py`。正式录音来自保留的 CC0 输入，署名/来源详见音频目录 README；不公开再分发源录音、PNG、UE/Fab/NiagaraExamples 包或插件。

穿心箭音频的最终保存状态见本目录 `delivery-state.json`，与历史 SelectedH 文档分开记录。首次补保存遇到用户正在 Play 的编辑器，UE 拒绝保存；未终止试玩。用户随后明确结束试玩并授权保存，后续采用现有互斥和后台导入。导入脚本已增加 Play/未保存同资产保护。

## 归档与检查边界

[archive-manifest.json](archive-manifest.json) 记录本批退役文件的原路径、trash 路径、字节数、SHA-256、原因和保留替代物。只移动已确认替代的快照、一次性改码脚本和废弃候选；保留当前制作输入、许可记录及首次失败/最终成功的检查证据。没有删除正式内容、存档、构建产物或并行工作。

上一轮用户要求的复查：Editor/Game 构建成功，212 项持续消耗检查、95 项弓联机隔离检查、48 项弓修炼检查，合计 355 项通过，见 [复查报告](../../Skills/elemental-hold-network-review-20261027.md)。它们没有实际双端 socket、延迟丢包、晚加入/重连或画面验收。本轮仅执行用户要求的归档、补丁重建/大小/敏感内容/许可及 Git 发布检查，没有重跑玩法测试、没有重新打包。

发布从原工程直接进行，使用独立 Git 索引保留其他暂存；只普通推送 `HEAD:main`，成功后回读远端 SHA。公开提交是源码资料与恢复材料，不是完整二进制工程备份。
