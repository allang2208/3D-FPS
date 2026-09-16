# 第四段柄尾配重砸击与武器命中音：发布记录（2026-09-16）

用户确认动作与音效「达到预期 / 成功了」后的整理与发布。按 [清理与发布](../../skills/ue5-weapon-workflow/references/publication.md)
的范围规则执行：按明确路径提交，不夹带并行功能，二进制与无再分发许可的音频只留本机。

## 本次提交范围

- 新案例 `SourceAssets/MeleePommelAttack20260916/`：动作规格 `pommel_motion.py`、作者脚本 `author_pommel_strike.py`、
  参考帧取用脚本、校验与渲染脚本、数值（`verification.json`、`attack_comparison.json`、`authoring.json`、
  `source_inspection.json`、`import_receipt.json`）与案例 README。
  可编辑 Blend、导出 FBX、参考视频与帧、评审渲染 PNG 受 `.gitignore` 排除，只在本机保留。
- 新案例 `SourceAssets/WeaponHitAudio20260916/`：mp3→44.1 kHz WAV 转换说明、`import_hit_audio.py`、
  `check_paths.py`、`run_import.ps1`、回执与 README。WAV 源与导入后的 SoundWave 只在本机保留。
- 新原生头文件 `Source/FPSGAME/Weapons/RuneSwordPommelRhythm.h`：第四段阶段钟、抬臂/砸出时间窗与 24 cm 前踏常量。
- 文档：`Docs/Weapons/runesword-pommel-strike-20260916.md`、`Docs/Audio/weapon-hit-cues-20260916.md`。
- 归档清单 `Docs/Weapons/melee-pommel-archive-20260916.json`：20 个废案文件（被否定的举锤版资产备份、首版评审渲染、
  读图临时副本），移动前后 SHA-256 一致，原件在 `trash/melee-pommel-strike-superseded-20260916/`。
- 技能沉淀（同时同步仓库镜像 `skills/`）：`ue5-fps-arms-animation/{SKILL.md, references/validation.md,
  references/two-handed-melee.md}`、`ue5-weapon-workflow/references/{melee.md, gunplay-vfx.md}`。

## 未包含在本次提交（仍在工作区）

第四段与命中音的**运行时改动**分布在共享文件：`RuneSwordComponent.h/.cpp`、`FPSGAMECharacter.h/.cpp`、
`FPSGAMECharacterCombatFeedback.cpp`、`FPSImpactFXSubsystem.h/.cpp`、`FPSBallisticsComponent.cpp`、
`PistolDualWieldCombat.cpp`、`Content/ColdSteelData/items.json`。

这些文件里同时存在 2026-09-15 那条**尚未提交**的「寒晶剑模块化 + 近战数值」与「步枪惯性/冲刺」工作，
而本次第四段代码依赖其中未提交的基础设施（`FMeleeModifiers`、`ColdSteelModularSword`、`ModularSword`、
`MeleeWeaponStats.h` 等）：单独摘出会产生编译不过的提交。因此这些代码随那条线一起提交，
不在本次发布内；本次发布的是案例源、数据、文档、归档清单与技能沉淀，二者不冲突。

`Source/FPSGAME/Building/VoxelBuildWidget.cpp` 里为解开 Unity 拼包同名函数冲突（与 `VoxelBuildComponent.cpp`
的匿名命名空间 `NumberKeyIndex` 重名导致 C2084、构建连续失败），把该函数改名为 `WidgetNumberKeyIndex`
（含唯一调用点，无行为变化）。该文件属于 voxel 那条线，未纳入本次提交。

## 构建与导入记录

- 动作：21:13:45 导入 `/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike`（1.60 s，
  初版姿态家族 + 抬臂蓄力 + 24 cm 前踏），入口 `run_import.ps1`（ImportHost，编辑器关闭时）；
  裂隙网格 `WristRiftV3/SM_RuneRift_Pommel` 同一批次。
- 原生：21:15:39 与 21:17:06 通过；音效接线后 22:00:56 再次 `Result: Succeeded`。
  `Binaries/Win64/UnrealEditor-FPSGAME.dll` 内含 `S_MeleeHit_Quick` 与 `S_GunHit` 两个字面量，
  可确认枪械命中音与第四段专属打击音均已进二进制。
- 音效：`/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick`（0.384 s）与 `S_GunHit`（0.288 s），
  `LoadingBehavior = FORCE_INLINE`；路径经 `check_paths.py` 在工程内逐个加载验证。

## 状态声明

本记录描述的是**作者源、数据、文档与技能**的发布，不是完整可运行功能发布：运行时改动仍在工作区，
且在寒晶剑/步枪那条线提交后才会进入仓库历史。本轮没有运行游戏、没有听感验收；动作手感与音效强弱由用户实机判定。
