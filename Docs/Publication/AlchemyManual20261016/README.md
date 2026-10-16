# 物理配方手册整理与发布

本轮手册开发已结束。源码、后台构建、纸页材质修复及已授权的本机检查均已完成；余下跨机器公网与美术体验由用户验收。本次收尾仅整理文件、沉淀技能和检查 Git 发布范围，没有再次运行 UE、构建、游戏或审计。

## 发布范围

- 无背景模型阅读器、目录与语义排版、长按拖动、首末书签、捕获/关闭生命周期，以及通用双面骨骼纸页模板。
- 文字和图片固定绑定于同一张翻动纸页，翻页结束只交换逻辑角色，不在落下后重新绘制或替换可见纹理。
- 正式代码修复：异常公共页码直接拒绝；客机 Pawn 销毁后，按同一已支付批次清除遗留工作台状态，避免手册保持打开和旧页码残留。
- 原创作者/导入脚本、许可归属、已有流程/联机审计源码、检查摘要及相关 SKILL。
- 补齐上一批 [药水工作台发布](../AlchemyWorkbench20261016/README.md) 所列的 12 个手册源码前置。共享 `VoxelBuildWorld.h` 只加入本手册审计需要的友元；共用打包配置只加入当前手册资产/字体目录。保留工作区中其它并行修改。

当前公共仓库仍沿用既有库存、角色、联机宿主与授权资产恢复边界，不是干净检出即可运行的完整二进制项目。本次没有为发布启动独立检出构建或重跑测试。

## 当前制作与恢复链

| 部分 | 保留源与入口 | 依赖与边界 |
| --- | --- | --- |
| 书本供体 | `PotionWorkbenchDesign20261015/ManualV3/AlchemyManual.blend` 与该目录作者脚本/归属 | evildeer Magic book set，CC BY 4.0；共享原始输入仍保留 |
| V5 纸张、闭合书、图片与字体 | `AlchemyManualFinePress20261016` 的 author_fonts、author_surfaces、author_model、import_assets、install_assets | 仍是 V6/V9 的母版；字体为派生 Alchemy Folio Serif，保留 Noto Serif SC 的 OFL、改名与来源 |
| V6 实体书签及纹理 | `AlchemyManualReadingFit20261016` 的 author_bookmarks、author_textiles 及导入脚本 | 读取 V5 Blend，生成当前书签轮廓及几何参数 |
| V8 等比例印字和书签材质 | `AlchemyManualContinuousTurn20261016/author_bookmark_print.py`、`import_bookmarks.py`、import.ps1、install_assets.py | 保留 V6 法线/粗糙度与已修正的顶点到像素插值、可读性补光；旧静态/WPO 纸页段已从导入入口分离并归档 |
| V9 双面骨骼纸页 | `AlchemyManualPersistentLeaves20261016` 的 author_model、import_assets、install_assets | 固定 UV、31 节纸页骨骼；导入时 SkeletalMaterial 数组逐索引写回，实际材质接口已修复并保存 |
| V10 书壳 | `AlchemyManualBindingTangents20261016` 的 author_binding、repair_binding_uv 及导入脚本 | 从 V9 作者源取书壳，只修复新增面主 UV；V9 作者脚本也调用此 UV 修复函数 |
| 原纸页包的槽修复 | `AlchemyManualLoadRepair20261016/repair_material_slots.py` 与 save_headless.ps1 | 仅在需要修复历史错误包时使用；当前导入脚本已包含正确写回 |
| 通用组件及阅读器 | `Source/FPSGAME/Building/BookLeafComponent.*`、AlchemyManual 系列、`UI/ColdSteelAlchemyBook*` | 当前目录与配方来自游戏数据，私人阅读不更改制作事务 |

作者目录位于 `SourceAssets/`。导入共用 `PotionWorkbenchDesign20261015/IntegrationV1/UEImportHost`，它是保留的本机依赖，不在本次清理范围。恢复按上表从供体、V5、V6、V8、V9 到 V10 顺序；不要重放退役 V4/V7 或旧 WPO 纸页脚本覆盖当前源码。

当前运行包为 V5 纸面与闭合书、V6 书签、V8 书签材质、V9 纸页、V10 书壳；翻纸声音沿用 `RuntimeV2/Audio/SW_AlchemyPage`。移除的仅是 V4/V7 过时强制 Cook 条目，正式 Content 包仍保留本机。

模型、Blend/FBX、PBR/图标、字体、UE 包、临时用户目录、完整日志及构建产物不公开。作者脚本与说明不包含这些二进制；[归属说明](../../../SourceAssets/AlchemyManualPersistentLeaves20261016/ATTRIBUTION.md) 保留许可和改作来源。Wawa Sensei 示例只作为设计思路参考，没有复制其代码或网页运行时。

## 归档与技能

404 个确认退役文件，共 113,479,977 字节，移至 `trash/alchemy-manual-retired-20261016/`。包含旧快照、V4 模型/纹理/制作入口、V7 材质修补入口、V8 静态翻页、旧构建/回执驱动以及已完成的隔离测试用户目录。移动前核对绝对路径和重解析点，逐文件记录来源、目标、大小、SHA-256、原因与替代物，移动后读回散列一致。

完整清单在本机归档根的 `archive-manifest.json`；本目录 [归档摘要](archive-summary.json) 记录数量、字节数和清单散列。最终回执、外层审计日志、关键失败证据、采用中的母版和正式 Content 均留在原处。历史文档提及的旧文件可经归档清单恢复。

个人技能与工程对应部分同步更新：

- [物理书本阅读器](../../../skills/ue5-ui-umg-slate/references/physical-book-reader.md)：持续纸页绑定、输入/释放边界及混合版本恢复。
- [工作站生命周期](../../../skills/ue5-cpp-gameplay/references/multiplayer-lifecycle-and-coverage.md)：Pawn 失效后以批次身份清理，保护有效的新操作者。
- [建模导入约束](../../../skills/asset-model-workflow/references/blender-hardsurface-checklist.md)：主 UV 通道冲突、空材质接口及 struct 数组写回。
- [联机检查场景](../../../skills/ue5-debug-validation/references/multi-process-runtime-evidence.md)：合法档案/角色前置、正式退出钩子和同时进程数边界。

## 已有证据与剩余验收

完整本机工程的 Editor/Game 构建均成功，回执为 `AlchemyManualNetworkAudit20261016/20261016-230749/result.json`。单机手册 89 项检查通过；真实 socket 联机 10 阶段、19 次端侧状态核对通过，涵盖客机正反翻页、异常请求、暂停/恢复、断线合书、主机接手、晚加入及旁观者拒绝。结果位于该目录 `Records/sockets-20261016-230922/host.json`，细节见 [覆盖记录](../../UI/alchemy-manual-network-audit-20261016.md)。

这些是整理前的历史结果。本机多进程检查最多两端同时运行，尚未进行跨机器公网、异常网络和打包专用服验收；实际外观效果以用户画面为准。当前不再继续这些测试，也不把本机整合构建当作公开提交切片的独立构建证明。
