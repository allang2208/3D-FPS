# 手套整理与源码发布

2026-09-27，用户反馈当前手套「基本 ok」，授权废案归入 trash、沉淀 SKILL、检查仓库整理和推送规则后发布到 `allang2208/3D-FPS`。范围为本轮露指手套、皮革裁片与两款图标迭代；其他并行武器、技能、地牢及 UI 工作不随此批发布。

## 正式版本与恢复

- 棕色物品 `ue_field_gloves` 为 `TailoredFingerlessV1`，22 套原生绑定、44 份独立／组合骨骼网格、3 组烘焙材质和单只空手套掉落模型。穿戴路径使用组合网格，Leader Pose 复用已有动画。
- 当前棕色基础防御 2、每级增量 0.5，近战攻速与换弹速度各加成 10%；黑色保持基础 4、每级 1、各 5%。原强化取整规则保留。
- 图标保持原目录 PNG 路径，单只空手套。黑色保持全指；棕色从真实指根开口、虎口和腕口显示皮革，不出现皮肤、不叠放第二只。
- 正式制作顺序：`author_tailored_fingerless_family.py` → `save_tailored_fingerless_family.py` → `import_tailored_fingerless_family.py`，均位于 `Tools/ModularOutfit/`。代表样件由 `tailored_fingerless_candidate.py` 和 `build_tailored_fingerless_candidate.py` 制作；导入库 `import_tailored_fingerless_candidate.py` 仍由正式入口复用。
- 源根 `SourceAssets/ModularOutfit20260927/TailoredFingerlessV1/`；UE 根 `/Game/Characters/ModularOutfit20260924/TailoredFingerlessV1/`。恢复其 Blend／FBX、材质、贴图、导入回执及全部原生骨架依赖，再使用精确物品配置；仅克隆 Git 不提供完整可运行资产。
- `ColdSteelProfileRuntime.cpp` 读档时更新旧棕色物品的名称与外观字段，保留实例 ID、位置、数量、强化与属性；沿用现有 A/B 存档事务，不直接编辑本机存档。

保留 `FingerlessHuntV2/FullShell`、`SkinCoverage`、原生输入与 `TailoredFingerlessCandidate`：它们仍提供当前覆盖、权重、拓扑、UV、扫描烘焙及选定图标场景，不是按名字可以删除的废案。历史 `FingerClearance`、`SavedFingerRefinement`、`CuffArmClearance`、`CuffShoulderClearance` 和最终 `ClearanceAfter` 保留已采用的旧动作修复来源／恢复轨道与证据，不在本轮重跑。黑色及 V7 原始装备链保留。

## 废案归档

共 126 文件，931,140,275 字节（约 888 MiB），移入本机 `trash/tailored-gloves-retired-20260927/`，逐文件保持原目录结构，移动前后 SHA-256 已读回匹配。详细路径、大小、散列、原因及替代物见 [归档清单](tailored-gloves-retired-manifest-20260927.json)。归档包括未采用的袖口缩放／腕部重分区脚本与作者产物、指根覆盖扩大前快照、旧手套图标场景与图像，以及已有正式 Blend 的自动备份；不删除原文件内容。

历史文档中的 `GloveBalanceIcons`、`CoverageToRoots20260927/Before`、`ClearanceReview/CoupledUnrelieved` 等路径对应的退役文件现按清单从 trash 恢复。正式源码不再读取这些覆盖备份。选定候选、正式图标、材质源、当前模型、已采用动作及其恢复数据保持原路径。未移动正在运行的 UE 进程可能管理的 Content 资产。

## 公开范围与许可

发布 C++ 装备覆盖与旧物品外观同步、目标物品 JSON、制作／导入脚本、文档、技能和归档索引。共享 JSON 与 C++ 仅暂存本次条目／片段；不整文件夹带高地剑、法杖、快捷攻击、仓库和其他并行更改。

Manny 派生几何、原生骨架／动作、Quixel Top Grain Brown 扫描及其烘焙图、Blend／FBX／UE 包、密集作者 JSON、采样动作、图标 PNG、回执、日志、编译输出和 trash 保留本机。商用使用权不等于允许在公开源码仓库再分发原资源；本次没有新增公开二进制许可。

## 状态与规则

此前 Game 与 Editor Development 构建成功，全部新家族资产已后台导入保存；用户随后反馈基本满意。此次只整理文件、技能并执行用户要求的推送检查，没有重新编译、启动 UE／游戏、截图、渲染或进行穿模验收。9 月 26 日旧覆盖形状的检查记录不能替代当前裁片款的测试结论。

按 `WORKFLOW.md` 第 8 节核对目标和主线、检查全部待推提交、暂存内容、大小、敏感信息与许可，普通非强制推送 `HEAD:main`，成功后回读远端 SHA 及 Godot 归档标签。技能同步工程镜像与个人目录；发布记录以实际 Git 提交为准。
