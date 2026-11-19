# 技能树、子专精与快捷栏数字键（2026-11-15 至 11-17）

本批保存全屏技能树（P）、火球／元素箭子专精、游戏开发式顶部金色提示、快捷栏退役 Q/E/X 的源码与恢复材料。GitHub 只保存文本源码、配置与规则；UE 资产、临时截图和构建日志不公开。

## 内容

| 范围 | 处置 |
| --- | --- |
| 11 个技能树专属源文件 | 直接发布，见 `Source/FPSGAME/`：`Skills/ColdSteelSkillTree*`（数据、迁移、判定、专精）、`Skills/ColdSteelSkillTreeLayout*`（网格与连线路由）、`UI/SColdSteelSkillTreeCanvas*`（自绘）、`UI/ColdSteelSkillTreeScreen/Detail/Sources.cpp` |
| `Content/ColdSteelData/skill-tree.json` | 直接发布：分支、阶位、前置、专精节点与数值 |
| 26 个共享宿主增量 | `Integration/*.patch`：`ColdSteelStatusModel.h`、`ColdSteelInventoryTypes.h`、`ColdSteelProfileRuntime.cpp`、快捷栏／快捷拖拽／底部栏布局、提示控件、火球与元素箭模型、联机合并等 |
| 规则沉淀 | `Skill/ue5-skill-magic-workflow/`：技能树工作流与 11-17 版式、联机同步记录 |

## 接入边界

- 补丁基于本机 `34c08285`（2026-11-17）。远端 `main` 在此之后又前进了 5 个提交（至 `db189895`），其中包含对 `ColdSteelStatusModel.h`、`ColdSteelInventoryTypes.h`、`ColdSteelProfileRuntime.cpp`、`ColdSteelHUDWidget.*`、`ColdSteelSkillPage.*` 等宿主的并行改动。**不要直接 `git apply`**；按 `integration-manifest.json` 的记录把技能树相关 hunk 合入当时的宿主。
- 技能树还依赖另外两批尚未合入公共主线的内容：`ColdSteelSkillProgression.cpp`（`ColdSteelSkills::Migrate/Validate/AddExperience` 拆分）与 `ColdSteelSkillPagePrivate.h`、`ColdSteelTreePanel.*`、`ColdSteelMagicWheel.*`、`ColdSteelMagicConfigurationHUD.*`，均在 [代码与 SKILL 清理](../CodeSkillCleanup20261118/README.md) 与其他批次里。只合并本批不足以编译。
- 需要一次 `FPSGAMEEditor` 原生构建。本批最后一次通过构建为本机 `Saved/BuildEditor/skilltree-fixes.out`（2026-11-17 22:47，Result: Succeeded，包含镜像专精保留、F6 习得、失败提示、窗口自适应四项修复）。该构建属于完整本机工作区，不代表公共主线可构建。

## 未验证

技能树的开树、选卡、专精投点、快捷栏拖放、联机双端同步均**未经实机测试**，由用户验收。

## 归档

本次退役文件移入本机 `trash/skill-tree-panel-20261117/`（5 份：旧备份、一次性脚本、两份中间构建日志、被否决的环形 V1 截图），逐件记录原路径、字节与 SHA-256。`trash/` 不进 Git。
