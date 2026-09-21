# 技能、施法与飞剑整理发布（2026-09-22）

本次发布本对话的闪电、圣光、推掌 V9、环绕飞剑连发与碎裂、火球燃烧，以及陨星/灼锋焰甲制作。保留其他任务在角色、韧性、装备、自动存档及场景系统中的未提交修改，共享文件按片段暂存。

## 现用版本与恢复

- 闪电：`Tools/Skills/build_lightning_assets.py`，`/Game/Skills/Lightning`；圣光：先 `build_holy_light_assets.py`，再 `polish_holy_light_assets.py`。图标/音频准备入口和来源见各迁移说明。
- 推掌：运行时由 `FireballCastMotion.h`、`FPSCastingMeshComponent.cpp` 和 `fireball_hand_pose.json` 驱动；`SourceAssets/FireballCast20260914/author_cast.py` 从同一参数输出 `CastingPalmPush20260921/ImpactV9`。需要本机 Manny 与 GASP 手臂作者源，不从 Git 自动取得。保留 1 秒动作预算及连发追加停留。
- 飞剑：`SourceAssets/RuneOrbBlade20260921/build_blade.py` → FBX → `Tools/AssetPipeline/import_rune_orb_blade_v2.py`。图标仍由旧源目录 `RuneOrbBlade20260920/build_icon.py` 制作。运行时新网格路径不变。
- 火球：当前 `build_fireball_torch_burn.py` 的材质、主体、拖尾三阶段已挂入 `build_fireball_assets.py`；恢复源包、球核及火把材质依赖，不能仅恢复外焰。
- 陨星/焰甲：初版 → PolishV2 → SplineV4 → RealisticV5 的系统容器链仍需保留。主体另走 `build_meteor_realistic.py` 的 RealisticV3 写实岩体；具体依赖和阶段见 [资源恢复](../AssetSetup.md) 与 [RealisticV5](fire-magic-realistic-v5-20260922.md)。

旧系统虽然不再作为最终火焰，仍被当前作者脚本复制或导入函数，不归类为废案。第三方材质/系统的完整导出、模型、贴图、音频、Blend/FBX/uasset、私人照片及构建/MCP 回执均保持本地；公开源码不是完整资源备份。

## 归档

共 80 个确认退役的源文件（883.4 MiB）移至 `trash/skills-magic-publication-20260922/`，目录下保留原相对路径。清单 [archive-manifest.json](../../SourceAssets/SkillMagicPublication20260922/archive-manifest.json) 记录每个原路径、目标、字节数、SHA-256、原因及替代物；移动后已逐文件回读哈希。包含被替代的推掌导出/旧姿态记录、粗版飞剑制作文件、黑焰修复前备份及下载的 GitHub 研究快照。现用资产、共享母版、当前可编辑源及有效重建依赖保留原位。

## 技能沉淀与交付边界

个人技能与工程镜像同步：魔法技能补充原火焰材质的 SubUV / 动态输入、曝光和容器依赖；手臂引用区分当前 V9 与历史版本；武器技能补充连发手势延长、属性快照、弱点判定和碎裂时机。

本次只执行用户授权的归档和发布检查。制作阶段的构建记录保留在原文档中，不视为本次重新构建或实机通过；未启动 UE、PIE、游戏测试或验收渲染。公开提交仍需按资源恢复说明准备本地合法素材。

发布检查：完整暂存清单为 148 个文本文件（约 1.21 MiB），已检查暂存差异、空白错误、JSON/Python 语法、项目内 include 的已发布依赖、文件大小、敏感凭据模式及忽略规则；未包含二进制、完整第三方导出或 trash。必要的武器伤害上下文声明/实现随调用链一并发布；后续韧性、金色符文、自动存档和身体组件改动仍留在工作区。检查回执在本机 `Saved/SkillMagicPublication20260922`。
