# 地牢性能与区域提前准备发布

本批收束 2026-10-14 至 19 日的地牢性能排查、F6 采集修正和区域提前准备。保持画质、怪物数量、波次、奖励和战斗规则。没有在本次仓库整理中启动 UE、运行游戏或补做性能/联机测试。

## 已保存的改动

- 身体、类默认资源和库存优先占用预加载额度；包/对象路径统一去重，互斥备用武器候选默认不常驻。生成器排除作者工具和诊断代码的非装备路径。
- F6 可选采集包含 UE 时间线、WDDM 状态及 Morph 缓冲身份；Start/Stop 在游戏线程执行，后台收尾写盘。采集跨 World 保留，清空帧窗口不再截断 trace，导出记录实际窗口交集。
- 修复退出 PIE 时编辑器空场景仍保留 Niagara GPU FXSystem 的生命周期问题；保留正常场景恢复和原显存节省策略。冻结尸体才使用适用材质的刚性阴影缓存，重新变形立即恢复；闲置体素图标预览释放渲染场景。
- 玩家状态通知仅标记装备待比较，避免无关属性刷新重建装备和蒙皮缓冲。
- 区域准备在入口通道提前进行，锁门提交全主题首波，通过原队列分批激活。世界共享 16 实例/256 MiB 估算增量预算，保留 CPU/提交/GPU 余量。有效压力与缺失样本分开；低优先级先回收；所有房间完成后停止维护；专用服务器提前跳过渲染查询。

## 发布方式与恢复边界

[source-manifest.json](source-manifest.json) 列出按源码路径发布的文件和本批提交切片的 LF 散列。对共享身体、Nurse、SKILL 入口及 AssetSetup/Backlog 文件只重放本批修改，不提交工作区中的其它改动。

[runtime-integration.patch](runtime-integration.patch) 保存 11 个有未发布前置的文件：区域/房间接入、共享调度器、新准备实现、货运取消、加载预算策略及炼金构建阻断的两行重命名。补丁不发布区域首领、门禁方向、货运玩法或炼金姿态的整套并行差分。

[integration-manifest.json](integration-manifest.json) 按文件记录基线、结果和 LF SHA-256。部分基线是从当前本机区域框架剥离本批性能改动后重建的前置文本，**不是公开 Git HEAD，也不冒充历史修改前快照**。恢复用前置保留在本机 `Saved/DungeonPerformancePublication20261019/Prerequisites/`。

恢复顺序：取得对应区域/联机/加载前置版本，核对 manifest 中每个文件散列，再使用零上下文补丁 `git apply --unidiff-zero`；新文件应不存在。当前本机源码已包含所有结果，禁止重复应用。相同源码路径在此前发布目录中的补丁是历史切片，不应无条件叠加。

公开切片仍不是可以脱离前置代码和许可资产独立编译的完整游戏。本机成功构建覆盖的是完整整合工程；不能当成这份公开 checkout 的构建证明。继续按 [资源恢复说明](../../AssetSetup.md) 取得 UE 5.8、项目插件、模型、动画、材质、场景目录和区域框架。生成的全工程预加载表含并行武器素材路径，本批只发布生成器和默认准入策略；恢复完本机来源后再用 `Tools/Performance/generate_preload_registry.py --write` 生成匹配版本。

## 证据与尚未完成部分

- 最新实现：[区域提前准备](../../Performance/area-spawn-preparation-20261019.md)，[逐路径与联机复核](../../Performance/area-spawn-preparation-review-20261019.md)。
- 根因边界：[共享缓冲、描述符堆与资源持有](../../Performance/shared-buffer-residency-and-driver-findings-20261019.txt)。旧持续慢态与另一轮驱动提交长帧是两类证据；约 392 MiB 的逻辑资源减少不等于物理显存减少同量，不证明 FPS 或持续 GPU 慢态已根治。
- [build-summary.json](build-summary.json) 摘录已完成的本机 Editor/Game 构建，不包含原始日志或二进制。最终 Editor 16.99 秒、Game 651.31 秒；本轮没有重跑构建。
- 服务器准备池不等于客户端实例缓冲准备。特殊怪完整附属 GPU 预热、客户端每实例缓冲提前准备、逐堆 WDDM 物理驻留映射以及实际分路/迟到/换图运行覆盖仍未完成。
- 其它日期报告保留为历史证据，以本页和 10 月 19 日复核为当前状态入口；旧“两个实例”等策略不再作为现行参数。

## 归档与技能

[archive-manifest.json](archive-manifest.json) 记录 276 项的原路径、归档路径、大小、SHA-256 或联接目标、原因及替代物。归档位于 `trash/dungeon-performance-retired-20261019/`，文件移动后核对散列。临时 FrozenHost 的原始 A2/B2 样本随宿主保留在归档中；Content/Plugins 联接没有被递归遍历，正式资产未移动。生产代码、其它有效采样、崩溃记录和最终构建回执保留。

旧报告引用的 `Saved/.../Before` 与 `Saved/ReceptionGpuDiagnosis20261018/FrozenHost` 通过该清单恢复。2026-10-14 旧报告提及的另一归档路径，本轮未在当前位置找到；本轮没有据此删除任何文件，也不把旧报告的归档声明当成此次搬移结果。

个人与工程技能同步新增 [共享输出缓冲归因](../../../skills/ue5-performance-packaging/references/shared-skinning-buffer-diagnosis.md)、[区域有界准备](../../../skills/ue5-performance-packaging/references/area-spawn-preparation.md)，并在性能及联机入口接入。技能只保留可复用决策与边界，详细采样数值留在工程报告。

本批不发布 UE/插件二进制、许可资源、DLL/PDB/EXE、ETL/utrace、完整崩溃上下文、原始日志或 trash 文件；归档清单仅为恢复元数据。提交前仅做用户要求的范围、补丁、大小、敏感信息与仓库规则检查。
