# 非缓存优先清理完成记录 — 2026-10-03

用户明确要求优先清理上一轮列出的四类文件。本次范围固定在原候选清单，刷新源码/文档引用及文件状态后没有扩大到新文件。

**已永久删除 24,807 个文件，合计 20,194,140,601 字节（18.807 GiB）。**

| 类型 | 删除文件数 | 删除 GiB |
| --- | ---: | ---: |
| 字节完全相同的 .blend1 自动备份 | 8 | 0.450 |
| 已归档并记录替代物的废案 / 一次性脚本 | 28 | 0.391 |
| 历史录屏长序列 PNG 原始帧 | 24,384 | 17.459 |
| 旧且无明确引用的崩溃转储 .dmp | 387 | 0.508 |

D 盘可用空间：执行前 63.522 GiB，完成后 81.875 GiB。删除文件的逻辑大小与磁盘可用空间增量可能因 NTFS 分配及其他程序同时读写而不同。

## 历史录屏范围与保留

| 原输出目录 | 删除 PNG 数 | 删除 GiB |
| --- | ---: | ---: |
| `Saved/RifleSprintAudit` | 6,237 | 4.288 |
| `Saved/TraversalRuntimeAudit` | 4,706 | 3.251 |
| `Saved/MonsterStairs` | 4,714 | 3.115 |
| `Saved/AKMIntegrationAudit` | 4,321 | 3.007 |
| `Saved/SkeletonStockAudit` | 475 | 0.902 |
| `Saved/SVDFirstReload` | 2,331 | 1.793 |
| `Saved/QBZ191IntegrationAudit` | 1,600 | 1.104 |

只删除 10 月 1 日前、20 帧以上的连续编号 PNG 中列入原清单的冗余帧。每个序列保留首帧、约四分之一、中间、约四分之三、末帧五张原图；保留具名截图、短序列、现存代码/文档明确引用的具体文件，以及所有 GIF/MP4、音频、日志、JSON/CSV、报告和脚本。七个目录保留 7,196 个文件，约 3.083 GiB。

样本与已有预览不能恢复完整的旧原始帧序列。本次没有补拍或重新运行游戏。

## 备份与废案的保留边界

八个 .blend1 在准备阶段与以下保留正式源的 SHA-256 完全相同，执行阶段再次确认正式源散列；只删除备份，正式 .blend 留在原目录：

- `SourceAssets/ArmsRepair20260909/SK_ArmsRepair_weights.blend`
- `SourceAssets/CantedForegrip20260911/CantedForegrip_Concept.blend`
- `SourceAssets/CantedForegrip20260911/FirmGrip/A_M4_Canted_idle.blend`
- `SourceAssets/M4InfimaRigRepair20260909/SK_M4_Infima_RigRepair.blend`
- `SourceAssets/PrismHandstop20260910/GripAnimation/A_M4_Prism_idle.blend`
- `SourceAssets/PSO1Russian20260923/PSO1_A762_Editable.blend`
- `SourceAssets/PSO1Russian20260923/PSO1_AKM_Editable.blend`
- `SourceAssets/VerticalGripClass20260911/prism/A_M4_Prism_idle.blend`

两组原有归档只清理已登记 payload，保留 README 与原归档清单。M10 的当前 V7 动作、V1–V5 制作依赖及 V6/V8/V10 烟雾恢复链保留；消耗品的正式模型、贴图、图标、动作输入与 UI 实现保留。旧 trash 的说明追加本次删除记录，历史归档不能再视为完整备份。

崩溃文件只删除原先批准的 387 个旧 .dmp；保留日志/XML、10 月 1 日及之后的全部崩溃、最新十组以及源码/文档明确引用的历史诊断案例。

## 执行与记录

逐文件记录原路径、绝对目标路径、大小、SHA-256、原因及保留替代物；先移入本次新建的 trash/payload，再读回散列。确认保留清单仍存在、新 payload 不含链接且文件路径/数量/总大小完全符合清单后，仅递归删除该明确目标。

- `trash/noncache-priority-cleanup-20261003-01a1018d/manifest.json`：实际候选、每文件散列、保留物、引用来源与原因。
- 同目录 `approved-candidates.json`：用户批准时的原始候选快照。
- 同目录 `events.jsonl`：实际移动与删除日志。
- 同目录 `summary.json`：完成状态、统计、执行前后可用空间。
- 同目录 `execute_noncache_cleanup.ps1`：执行过程存档，勿重跑。

所有 DDC、编译/模型/流体制作缓存、正式构建产物、模型权重、正式 Content、Source 及玩家存档未列入操作。Saved/Autosaves、Saved/Recovery、根目录失败保存 .tmp，以及没有证明重复的可编辑源继续保留。

没有由本任务启动、关闭或重启 UE；已有编辑器照常运行。本次只做获授权的文件清理与必要归档核对，没有编译、游戏测试或验收；游戏由用户自行测试。

完成时间：2026-10-03T21:10:35.2895109+08:00。
