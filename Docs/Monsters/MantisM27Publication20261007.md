# 螳螂 M27：整理、源码发布与恢复

2026-10-07，按用户要求整理本会话的螳螂制作、战斗和声音，发布到 `allang2208/3D-FPS` 的 `main`。设计名及 F6 显示为 **螳螂 M27**，稳定 ID 和蓝图路径保持 `MantisM27`、`/Game/Monsters/MantisM27/BP_MantisM27`。

## 当前有效内容

| 范围 | 当前版本 | 保留的输入 |
| --- | --- | --- |
| 造型与绑定 | BindingV2 的连续足部/镰刀权重 | 原三视图、用户 Meshy GLB/PBR、ProductionV1、BindingV2 拓扑/骨表/权重 |
| 追击跑姿 | RunV4 | BindingV2、原 Mutant3/Khaimera 动作与重定向样本 |
| 普攻 | ClawV16 强化横劈 | ClawV3 源，已认可的 ClawV14 恢复版本 |
| 飞扑 | PounceV11，头顶下劈、刀刃方向与左右分离 | BindingV2、PounceV5 → PounceV6 源及供体样本 |
| 隐身 | CloakV1 凝胶材质与独立影子 | ProductionV1 纹理、原材质制作配方 |
| AI/战斗 | CombatV15 | 原共享 BT/导航与玩家状态入口，见专项记录 |
| 声音 | AudioV1，15 个角色音效 | 原创合成脚本、三份已有 CC0 MP3 预览、来源哈希 |

首次接敌与半血各一次隐身、每秒恢复 5% 最大生命、恢复到 80% 后锁定接敌、攻击破影双倍、飞扑致残 5 s、接受攻击后 50% 概率一层流血，沿本机当前实现保留。近战基础 190 cm 经共享 1.5 倍后触达 285 cm；起手、停步与命中使用统一范围来源。普攻每刀 0.65 s、接触 0.25–0.30 s，飞扑三段 0.60/0.65/0.80 s。

用户认可的是 ClawV14/CombatV15 的普攻基础；ClawV16 横劈和 AudioV1 已保存，尚未获体验反馈。PounceV11 的历史方向诊断不是游戏验收。

## 归档结果

143 份文件、142,253,393 字节已移至 `trash/mantis-m27-retired-20261007/`，逐文件移动前后 SHA-256 一致。包含 ClawV7/V12/V13、PounceV9/V10 的退役源与工具/记录、旧保存副本、旧构建备份、失效 PID 和 Python 缓存。

11 个旧动画包在后台读取 AssetRegistry 后确认无外部引用，一同移入 trash。来源、目标、字节、散列、替代版本见 [归档清单](../Publication/MantisM27_20261007/archive-manifest.json)；工具为 `Tools/Publication/read_mantis_retirement_refs_20261007.py` 和 `archive_mantis_m27_20261007.ps1`。没有删除原始模型、当前绑定、当前声音或动作源。

保留旧版本的原因是实际依赖：ClawV16/V14 读取 ClawV3，PounceV11 读取 V6，V6 读取 V5；BindingV2 读取 ProductionV1。ClawV14 另为认可的恢复基线。历史文档里的原路径可按归档清单在 trash 找回。显式要求旧版方向对比时，V11 检视工具读取已归档的 V10；常规导入不再自动执行旧方向诊断。

## 公开范围与素材边界

公开 M27 C++、螳螂专属共享入口差量、原创 Python/PowerShell 制作配方、技能参考、说明和归档元数据。共享文件精确选择 M27 段落，不提交其他怪物、玩家死亡、热成像、符文或 APS 导航的并行修改。

原 Meshy 模型、用户概念图、FBX/Blend、PBR、密集骨骼/权重/动作采样、音频、UE 包、导入回执、日志和 trash 保留本机。Epic Paragon Khaimera/Mutant3 派生素材受其原许可约束，不作为 CC0 发布。三份音效输入是项目既有记录标注 CC0 的 MP3 预览，不是无损母带；来源见 [音效设计](MantisM27AudioV1.md)。公开 Git 是源码与恢复配方，不是完整资源备份。

## 恢复顺序

1. 恢复合法完整 UE 5.8.2 内容、用户提供的 Meshy GLB/PBR、原动作供体及共享怪物 BT/动画/布娃娃资产。原文件输入与拆取配方在 `SourceAssets/MantisM27/MeshyImport20261005V1/intake_source.py`；原 GLB 只有静态几何，Meshy 重拓扑不等于含骨架。
2. `read_authoring_sources.py` → `author_mantis.py` → `import_production.py`，再运行 `prepare_binding_regions_v2.py`、`rebind_mantis_v2.py`、`import_binding_v2.py`、`connect_binding_v2.py`；恢复阶段按脚本分别使用 Blender 或 UE Python。`finish_contacts.py`、`finish_lods.py` 是基础生产接入补充。
3. `read_claw_sources_v3.py`、`retarget_claws_v3.py`、`author_claw_v3.py` 建立 ClawV3；最新普攻由 `author_claw_v16.py` 和 `import_claw_v16.py` 保存。只需回到认可基线时使用 V14。RunV4 使用对应 `retarget_run_v4.py`、`author_run_v4.py` 和 `import_run_v4.py`。
4. 飞扑按 `retarget_pounce_v5.py` → `author_pounce_v5.py` → `author_pounce_v6.py` → `author_pounce_v11.py` 制作，最后导入 V11。`install_combat_v8.py` 恢复飞扑接触参数，随后 `apply_combat_v15.py` 覆盖最终近战范围。不要只运行早期安装器便当成当前版本。
5. `author_cloak_v1.py` 先制作材质，再带 `-M27ConnectCloak` 接回蓝图；保存当前 RunV4/技能移速配置。各历史安装器会覆盖自己负责的槽和参数，最终以当前版本为准。
6. 在已有 UE/构建释放后按共享批次门控完成原生 Editor/Game 构建。音效使用 `author_audio_v1.py` 制作，再由 `finish_audio_v1.ps1` 构建和导入 15 个 SoundWave、保存蓝图角色映射及名称。源预览副本位于 AudioV1/Sources，重新制作前按 manifest 恢复同一输入。

## 检查边界

AudioV1 开发阶段已完成本机 Editor/Game 构建、15 个 SoundWave 与蓝图实际保存。该构建对应当时完整工作区，不冒充本次精确公开快照的独立编译证明。本轮执行用户要求的发布检查：归档引用/散列、精确暂存差异、空白错误、文件大小、敏感内容、许可边界、远端与提交范围。未新增游戏、PIE、渲染、试听或验收。

公开路径清单在 `Docs/Publication/MantisM27_20261007/published-files.json`。推送日志和检查回执留本机 `Saved/MantisM27Publication20261007`。
