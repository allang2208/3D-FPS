# 衣物工作暂停与公开发布 — 2026-09-29

用户要求暂停排查，下个对话继续。**SVD 锁子甲右臂在 ADS/换弹进入镜头仍未解决**；核心待办见 [暂停交接](../Characters/svd-outfit-pending-20260929.md)。本次提交不是修复通过声明。

## 发布范围

发布本对话的手腕覆盖、内衬收边、针织/短袖作者配方、201/攀爬/各枪锁子甲修正配方、衣物候选关卡及相应文档。衣物配置只纳入这三款上衣、手腕覆盖和 201 所需部分；物品表只纳入两款上衣的名称、图标和掉落引用。C++ 只纳入短袖独立覆盖材质槽一处改动，保留其他会话的 Traversal 预载及其他运行层修改。

SVD 当前仍用 SVDShoulderOpening20260929，新的 SVDLODRepairCandidate20260929 尚未接入。源快照、动作姿态、图片、构建产物及 UE 包留本机；公开仓库不能单独恢复完整视觉资源。历史 publish/install 脚本仅用于追溯制作顺序，不要直接重跑覆盖当前 profile；新衣物入口是 garment_pipeline.py。

## 本机恢复依赖

- `Content/Characters/ModularOutfit20260924` 及各枪原生骨架、动作、材质、贴图；V7 裸臂和手套上游链。
- `SourceAssets/WristCoverage20260929`、`ChainmailInsetBinding20260929`、`FieldSweaterKnit20260929`、`LMG201Wrist20260929`、`ShortSleeveTraversalDiagnosis20260929` / `ShortSleeveTraversalFix20260929`、`ChainmailReloadFit20260929`、`SVDOutfitSpike20260929`、`GarmentFoundation20260929`、`SVDRuntimeDiagnosis20260929` 的本机几何/姿态/导入回执。
- `Content/ColdSteelData/Icons/FieldSweaterKnit20260929` 的现有图标及衣物拾取包。未经再分发许可核准，不公开这些派生二进制。
- 基准、候选和对比源不按日期或“旧版本”字样直接归档。当前只移动 11 个明确失败、被替代或已完成的一次性脚本/重复输出；散列与恢复路径见 [归档清单](OutfitPause20260929/archive-manifest.json)。

## 暂停与发布操作

临时 Slate 采集回调已注销，计数 ADS=0、reload=0；未留下后续自动采集。当前命名为 ADS/reload 的截图没有证实异常瞬间，不能用于通过记录。低 LOD 修正候选已保存，仅是候选。

本次仅做用户要求的归档散列、暂存差异、大小、敏感信息、许可范围、远端历史与推送检查，没有继续游戏排查、重开编辑器、重新构建或追加回归。既有文档中的离线统计是先前记录，不是本次重新测试。

共享暂存区出现独立附魔发布内容，因此本次使用 `D:/FPS3D/outfit-pause-publication` 临时隔离工作区；托管工作区工具因会话 cwd 不是 Git 根而不可用，按规则使用 Git 临时工作区。只提交本轮精确路径，普通推送 origin HEAD:main；成功后保留提交及发布补丁并移除该临时工作区。主工程工作文件和他人暂存不回滚，不向其他对话发消息。
