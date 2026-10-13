# 木工工作台源码整理与发布

整理发布：2026-10-14，功能制作记录截至 2026-10-13。差异筛选基线：`a0c381ceff508da0c6baeae8eb71d3eecf5c9272`；发布承接已推送基线 `2124b9974b8e38d984abe81b426bdbd3143b61db`。范围是木工工作台；共享文件只提交木工相关行，其他并行开发留在工作区。

## 当前实现

- 管理面板按铁匠流程使用顶部配方下拉、材料表、成品与属性预览、说明及底部操作，随背包抽屉滑入。进入实景加工后，结束返回管理面板领取或废弃；不保留练习入口。
- 正式配方为现有猎手长弓 `bow_dark` 与学徒长杖 `ue_apprentice_staff`，各消耗 2 木材。历史弓臂物品与改造配置仍有引用，保留兼容，不是新的正式配方。
- 支付、保存工件、暂停恢复、领取和逐材料向下取整返还一半沿库存事务完成。背包不足保留待结算工件。切割快照保存掩码、角度、位移、撤销及时间；恢复不再扣料。
- 调整时暂停计时，空格切换调整/加工；Q/E 每次 1°，精调 0.25°。现行达标条件为废料清除至少 80%、主体损伤不超过 20%，关键连接保持完整；弓 150 秒、法杖 120 秒，各 3 次撤销。
- 当前 V6 台面移开干扰摆件，删除悬空护罩和木板夹片，视角朝向主工作区。锯片外缘红漆与实景刀口指示使用实际几何/挂点；调整时虚线、加工时实线。
- 品质 `0.75 + 0.005 × clamp(score,0,100)`：50 分无修正，80 分 +15%，100 分 +25%，最低 −25%。弓修正物理伤害；法杖修正该件武器的魔攻贡献，不扩大到角色基础魔攻或其他装备。品质随成品保存并共用战斗属性求值。

当前规则以源码、`Content/ColdSteelData/woodworking*.json` 和本记录为准。`Docs/UI/woodworking-*`、`Docs/Building/woodworking-*` 是带日期的过程记录；早期练习、卡片、97% 阈值和护罩描述不代表最终方案。

## 联机公开范围与恢复前提

本机实现包含服务端切割评分、工件 ID 绑定、库存回执、序号与 Pawn 校验、分块快照、品质权威合并和断线收尾。木工独立源码直接提交；涉及未发布共享框架的接入修改保存在 [shared-framework-integration.patch](shared-framework-integration.patch)。

补丁基线是“当前本机共享框架去掉木工新增部分”的合成基线，**不是本次公共 HEAD**。各文件 UTF-8/LF 基线及结果哈希见 [integration-baselines.json](integration-baselines.json)。需先具备对应共享联机框架，再核对基线并合入；当前本机已经具有这些修改，不要重复应用。它不包含或替代共享框架本体。

恢复依赖包括 `ColdSteelAuthorityContext`、`ColdSteelStationNetwork`、`ColdSteelInventoryRequests/RequestTypes`、`ColdSteelProfileTransfer/Recovery`、`ColdSteelSharedInventorySubsystem`、队伍切图和玩家状态的当前宿主接口。随发布生成的 [source-dependencies.json](source-dependencies.json) 列出木工源码直接引用而公共基线尚未包含的本地头文件；更深层的共享框架依赖由其自身发布负责。当前公开提交是有依赖边界的源码交付，**不是可独立构建的完整工程包，也不是联机验收完成的声明**。

## 本机资产恢复链

原始输入由用户提供；本次未取得原模型与贴图公开再分发许可，因此只发布作者脚本、参数和来源记录。UE 包、ZIP、Blend、FBX、贴图、材质宿主、生产回执和构建日志保留本机。

1. 保留 `SourceAssets/WoodworkingBenchV2` 原始布局/材质输入，及 V4 的 `Input`、`Source`、`GameReady`、`ProductionRecords/blend_inspection.json`。V4 作者导出、材质导入与 LOD 脚本继续保留；旧 V3 收纳方案未启用。来源哈希见 [V4 接入记录](../../Building/woodworking-bench-v4-import-20261008.md)。
2. V5 `rearrange.py` 读取 V4 几何、材质、检查记录，生成清理后的台面。V6 `refine.py` 继续读取 V5 游戏版 Blend、布局参数和 V4 记录，再移除护罩/夹片并准备当前刀口。V2/V4/V5 都是恢复输入，不能整目录当废案删除。
3. V5/V6 的 `import_meshes.py` 与 `finalize_lods.py` 用于隔离宿主导入与落盘。当前材质创建入口为 V6 `paint_material.py`、`apply_saw_highlight.py`；后者要求 `Saved/WoodworkingSawHighlight20261013/MaterialHost`。恢复时先准备指定宿主及原材质输入，不把仅有脚本当已安装资产。
4. 正式台锯目录为 `/Game/Building/WoodworkingBenchV6Controls20261013`；刀口指示材质在 `/Game/Building/WoodworkingSawHighlight20261013`。`Tools/Building/register_woodworking_bench.py` 使用 V6 登记配置与布局出处更新调色板单个 `woodworking_bench` 条目，保留其他条目与已有放置字段。
5. 旧 `woodworked_bow_limb` 的图标制作脚本与本机图标保留；已有存档及弓改造仍会引用它。

V4 `ProductionRecords` 保存历史制作脚本，部分保留当时 `Documents/Codex/.../woodworking_v4_import_20261008` 的绝对宿主路径，`ue_import_meshes.py` 是依赖前段变量的脚本片段。跨机器恢复需先调整宿主路径并按原脚本组合，不直接逐个独立执行。V5/V6 布局文件为作者参数，原几何与贴图仍需本机输入。

## 归档与技能

147 份修改前快照和被下拉管理方案替代的练习/卡片设计已移至本机 `trash/Woodworking20261013/`。逐文件原路径、去向、字节数、SHA-256、原因及替代物见 [archive-manifest.json](archive-manifest.json)。归档移动前后核对哈希；trash 内容不进入 Git。有效模型恢复输入、当前实现及构建证据仍保留。

可复用经验已同步个人技能和仓库技能：

- [已支付工件与品质契约](../../../skills/ue5-cpp-gameplay/references/paid-workpiece-quality.md)：事务、恢复、半料返还、属性通道与服务端权威。
- [工作台面板](../../../skills/ue5-ui-umg-slate/references/crafting-workbenches.md)：铁匠复刻范围、下拉行生命周期、横向文字、TArray 别名与真实刀口提示。
- C++ 与武器技能入口增加上述引用；保留工作区其他会话的技能入口整理。

## 构建与未测试边界

既有 `Saved/WoodworkingQuality20261013/delivery.json` 记录本机完整工程 Editor 构建在 23:35:51、Game 构建在 23:36:19 成功。用户在品质追加前确认过锯齿高亮版本可用。上述记录不证明随后并行变更或本次精确公开子集可独立构建。

本次仅做用户要求的仓库发布检查：范围、暂存差异、二进制/大小、敏感信息、归档完整性与接入补丁应用一致性。不启动 UE、游戏、PIE、自动化测试或联机验收。最新品质与联机效果交由用户测试。
