# 面板工作流与废案归档 · 2026-09-13

本轮交付 [面板与栏目工作流](../../UI-WORKFLOW.md)、[规划模板](panel-column-plan-template.md)，并更新 [UE UI 技能](../../skills/ue5-ui-umg-slate/SKILL.md) 及个人技能镜像。新面板／栏目按当前黑灰玻璃规范先规划布局、数据和状态，再按授权阶段制作。

## 废案范围

只归档本轮相关、已被当前方案替代的文件。归档根为 `trash/ui-panel-workflow-20260913/`，内部保留原相对目录。完整原路径、目标、字节数、SHA-256、原因、替代物及移动后读回结果见 [机器可读清单](panel-workflow-archive-20260913.json)。

| 原文件 | 处理与保留替代物 |
| --- | --- |
| `Docs/UI/Concepts/EquipmentGunsmith-20260910/01-drawer.png` | 未采用的抽屉方案，归档 |
| 同目录 `03-compare.png` | 未采用的双枪对照方案，归档；正式面板保留右侧真实数值汇总 |
| 同目录 `04-loadouts.png` | 未采用的配装档案方案，归档；不引入概念中的新增玩法 |
| 同目录 `05-hotspots.png` | 未采用的热点方案，归档 |
| 同目录旧 `README.md`、`gallery.md`、`prompts.json` | 旧五方案及字体建议归档；原位置重建仅含已采用 02 来源的记录 |
| `Docs/UI/gunsmith-cold-glass-plan-20260912.md` | 旧背景与字体候选提案归档，替代为 [正式设计规则](ui-cold-steel-design-system.md) 和 [实际接入记录](gunsmith-cold-glass-implementation-20260912.md) |

共 8 个文件。已采用的 `02-workbench.png` 及九张 `SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/` 图标继续保留，10 个有效源图的大小／散列也列入清单。原枪械库背景、字体、UE 资源、生成来源、Saved 回滚与交付证据未移走。

## 发布边界

本轮发布工作流、正式规范、相关 UI 实现经验、技能、来源文字、恢复工具与归档清单。`trash`、PNG、字体、UAsset、缓存、构建产物和 Saved 证据继续留在本机，恢复边界见 [AssetSetup](../AssetSetup.md)。公开文档中的历史本机截图路径不代表仓库附带这些图片。

当前工作区包含并行 UI 和其他功能修改。本轮文档与经验发布不代表把所有运行时代码一起提交，也不声明远端克隆已具备本机全部 UI／资源状态。其他任务的已有暂存内容与未提交实现保持原状。

按用户要求只执行本轮仓库整理及推送检查；不启动 UE、不生成新预览、不运行游戏或业务回归。归档散列、发布差异和技能格式结果记录在本机 `Saved/UIPanelWorkflow20260913/`；游戏实际表现由用户测试。
