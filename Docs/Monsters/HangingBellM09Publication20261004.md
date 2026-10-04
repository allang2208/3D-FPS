# M09 悬钟：整理、恢复与源码发布

2026-10-04。按用户要求整理本对话的悬钟文件，归档明确废案，沉淀技能并发布到 `https://github.com/allang2208/3D-FPS.git` 的 `main`。本次遵守 AGENTS.md、WORKFLOW.md 第 4/7/8 节和 AssetSetup 的许可/恢复边界；不包含其他怪物、武器、UI 的并行改动。

## 当前有效版本

| 用途 | 当前内容及重建入口 |
| --- | --- |
| 基础身份与骨架 | 用户提供的 Meshy Bound Oculamoth；Source 原 GLB、Textures、V02 分件及 RigV03 的 113 根变形骨/8 个控制骨保留 |
| 身体与小手臂 | V13 归属修正 → V15 绑权 → V16 连续手腕与原闭合主体；`repair_arm_continuity_v16.py`、`finish_arm_continuity_v16.py`、`export_claw_continuity_v16.py` |
| 贴图绑定 | V22 修正已知 Body/Closure `_001` 空槽；`fix_surface_bindings_v22.py`，V16 制作/导入配方同步修正 |
| 护冠双爪 | V18 完整身体驱动，1.1 s 动作、0.35–0.55 s 接触；`author_claw_snap_v18.py` → `import_claw_snap_v18.py` |
| 三叠鸣震 | V07 六跳/5.6 s/20 m/每跳 SAN -2、柔边波面及音效；V09 分层展开 1.5 倍速覆盖 V07 动画路径；先 V07 配方，再 `author_resonance_opening_v09.py` 与对应导入 |
| 群眼凝视 | V08 动作/束与虹膜网格/音效，V10 汇聚粒子，V12 可见性修订；V12 复用 V10 作者脚本，源 HLSL 保留在 GazeV08 |
| 死亡与尸体 | V13 松手动作、包含真实 FBX 容器的原尸体物理体/约束，以及 HangingBell 专用阻尼；`repair_skin_death_v13.py` 和 `import_skin_death_v13.py` |
| 活体受击 | V23 独立膜片查询 Physics Asset、眼冠必暴、共用回执；`prepare_hit_surface_v23.py` → 原生构建 → `author_hit_surface_v23.py` |
| 移动与转身 | V20 110 cm/s 横移、120 度/秒转身及相应节奏；V24 关闭活体胶囊阻挡、连续顶面投影、平滑高度与抓点 |

正式资产仍分布在 `/Game/Monsters/HangingBellM09/V04,V07,V08,V10,V23`。资产路径的版本号不代表其内容仍是初版，例如 V04 的 SK_M09、Claw、Death 已分别更新。V04 通用待机、移动、钟摆、硬直和已有测试房继续保留；本次没有退役测试房。

## 必须保留的本机输入

- `SourceAssets/HangingBellM09Meshy20261003/Source/Meshy_AI_Bound_Oculamoth_1003131003_texture.glb`，原 SHA-256：`1bbac0246fa35e4a92ab9d0da5633658259e4ed1170e0de5cdd8fecc1d31a094`。来源为用户本地文件；未据此假定可公开再分发模型或贴图。
- V02 完整分件、RigV03 的 Blend、rig_recipe、rig_input、skin_weights，以及原材质/PBR。这些旧版本是实际输入，不是废案。模型保持约 189 万三角面，尚无性能 LOD，不因本次整理宣称性能验收。
- SkinDeathV13 的模型与死亡动作、CrownClawV15 的两个 Blend、ArmContinuityV16 的两个 Blend 和诊断 NPZ；V18 会读取 V16 动作，V16 又读取 V15，不能只保留最大版本号。
- CrownClawV11 的 `Records/donor_motion.json` 仍被 V15 作者读取。其源为本机 M07 `LibrarySweepV27/Motion/M07_LibrarySweep_V27.blend`，依赖已有合法 ZombieAnimationPack/M07 供体；V11 旧攻击成品已退役，但供体输入保留。
- 现有百目 `HundredEyedSlag/EyeChargeV14/NS_EyeConvergence` 及材质/粒子依赖，供 V10/V12 汇聚效果派生。相关通用作者助手在 `Tools/Skills/build_fireball_assets.py`、`build_fireball_flames.py`、`build_fireball_flight.py`，保持原本机内容依赖。
- 已保存的 UE 模型、材质、贴图、骨架、动画、物理、Niagara、音频和测试房，以及最新阶段制作/构建/保存收据。纯 Git 克隆不包含这些二进制内容。

恢复当前版本应先补齐上述本机输入和 UE 内容，再按表中依赖链制作；局部修订只执行对应阶段。不要在 V18/V22 上重跑整个 V04/V15 导入，把新动作或材质覆盖回旧版。V23 基础查询资产必须在带硬引用的新 DLL 首次加载前就位；恢复已有 V23 正式资产时无需再次生成。

## 废案归档

已将 **136 份文件，约 1965.06 MiB** 移入 `trash/m09-retired-20261004/`，保持原相对路径，逐文件核对 SHA-256。

归档包含：V01 独立分件成品、V06 旧鸣震制作包、V11 独立旧抓击成品（供体记录保留）、V17 旧抓击包、被替换的 V04/V07 动画导出、失败的 V16 局部补面脚本、修改前 Before/Blend 自动备份及已执行完的旧源码迁移脚本。详细来源、目的地、大小、理由与散列见 [归档清单](HangingBellM09Archive20261004.json)。

历史文档里的 `Before`、V06/V17 等旧路径按此清单恢复；本次没有删除历史设计文档。Content 内旧 UE 包没有按文件名直接删除：在未执行资产引用清理的情况下保留其兼容和恢复用途，避免伤及已保存蓝图/关卡。原始输入、完整有效源、最新成果均不进入 trash。

## 发布内容与状态

公开悬钟运行 C++、原创动画/导入/修复配方、四份原创 HLSL、历史修订说明、本归档索引和 `ue5-monster-workflow/references/m09-hanging-bell.md`。共享文件只提交悬钟所需的感知半径、SAN 扣减、暴击入口、尸体阻尼和 cook 目录增量；保留其他任务的工作区改动。

原 GLB、贴图、Blend/FBX、供体采样、密集网格/蒙皮/骨姿数据、导入传输回执和构建日志改为本机保留，不纳入本次公开提交；已经跟踪的同类文件仅从当前 Git 索引移除，现有有效本机文件仍在，不改写远端历史。

V23 历史专项检查为 363 项通过、0 失败，只覆盖受击和结算等指定范围；V24 已完成 Editor/Game 常规构建但未游戏测试。本次仅执行用户要求的归档、提交范围、敏感内容和推送检查，不重新启动 UE、不执行游戏或动画验收。个人与工程 SKILL 添加相同的 M09 专用参考，各自其他已有内容保持原样。
