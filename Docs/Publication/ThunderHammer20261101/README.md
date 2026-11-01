# 雷神之锤整理与发布（2026-11-01）

本批保存雷神之锤的专属攻击、投掷召回、疾雷、震霆、静电场、线圈、雷鸣/回响及雷吸开发成果，连同本轮联机修复、模型制作配方与工作流经验。发布目录为当前工程根目录；原始模型、PBR、音频、图标、动画和 UE 包保留在本机。

## 发布范围与共享依赖

- 专属 C++ 文件进入 `Source/FPSGAME/Production` 和 `Development`；独立共用修复按 hunk 提交。两张完整专属改造表、物品目录与伤害公式中的 `ue_thunder_god_hammer` 条目一起发布。
- 可公开的原创作者脚本、导入/落盘脚本和制作说明保留在 `SourceAssets/ThunderGodHammer20261028`。历史版本仍可能是当前制作的输入；不会按版本号清空。
- 共用战锤主体、角色动作、权威库存和部分伤害消费者包含其他在途工作。本批只把属于雷神之锤的差量保存为 [SharedHosts](SharedHosts/) 补丁，**没有将这些共享文件的完整工作副本提交到主线**。补丁要求各自记录的本地前置版本，不可直接套到干净 HEAD，更不能把裁剪副本覆盖本地工作文件。
- [source-manifest.json](source-manifest.json) 列出直接源码、配置键、作者配方与每份补丁的前置/结果 SHA-256（统一 LF）。这是一份可追溯开发发布，**不是已经独立构建通过的干净检出完整工程**。现有本地实现与已编译 DLL 未被发布裁剪改写。
- 主线仍需对应共用战锤与技能基础、角色表现/库存消费者及本地资源才能恢复完整玩法。按前置散列应用补丁后应由后续明确授权的构建/测试核验，不绕过缺失前置强行覆盖。

## 模型与声音恢复

当前贯雷为 `GuanLeiClosedCrownV12` 的 `V12_UV2`，疾雷为 `JiLeiInlaidLightningV14`；其保存切线修复和明确 Nanite 回退目标的脚本已保留。原始几何、法线、接口和可编辑源保留，未把高精度修复描述成减面或性能优化。

[asset-dependencies.json](asset-dependencies.json) 记录活动目录的资源路径及必须保留的制作输入。`GuanLeiPrecisionV11`、`JiLeiPrecisionV13`、静电场 V1/V2 仍有作者依赖；旧 `JiLeiSeatV1` 与 `RecallAudioV1` 仍有运行素材。当前划空/接锤作者输入为 `RecallAudioUserV4`，不要从已退役试听方案恢复声音。

本机工程入口是 `D:/FPS3D/FPSGAME`，其中 `Content` 联接到 `F:/FPSGAMEData/Content`；这些仅是当前宿主路径。公开仓库不含未经核准再分发的媒体、密集姿态/网格数据、缓存、存档或 trash。作者脚本需要清单中的本地输入与 UE/Blender 环境；脚本存在不表示资源已在另一台机器恢复。

## 可恢复归档

1,732 个退役文件、1,893,740,396 字节（约 1.76 GiB）已移到本机 `trash/thunder-hammer-retired-20261101`。包括旧隔离宿主构建/DDC、被用户音频替换的 V2/V3 方案、失败 UV 导出、自动备份、轮转日志和旧联机场景输出。

[cleanup-manifest.json](cleanup-manifest.json) 记录每个原路径、目标、大小、SHA-256、理由及保留替代物；本机 trash 下 `move-receipt.jsonl` 记录移动后逐文件散列一致。目录联接未移动，正式 Content、真实玩家存档、活动源模型/贴图、当前导出、最终检查回执和首个复制崩溃关键日志保留。归档发生在同一磁盘，不代表释放了同等磁盘容量。

## 已有检查与本次发布检查分开

此前用户要求的完整检查记录在 [Evidence/review_report.json](Evidence/review_report.json)：后台 Editor 构建成功；1,071 项隔离检查通过；监听服务器和专用服务器各 11 项独立进程 UDP 场景通过，每端 60ms 延迟、3% 丢包。两种模式的紧凑回执为 [监听](Evidence/listen-cases.json) 和 [专服](Evidence/dedicated-cases.json)。完整原日志与原相对路径仍按该报告位于本机 SourceAssets；本目录的副本不改变历史记录路径。

这些是此前本地完整工程的结果。本次整理不启动 UE、不重跑游戏、不把它们当成本提交的独立构建证明。无画面/静音网络运行没有验收动画观感、材质外观或音频混音；完整背包 UI 事务、真实换图、晚加入/重连、多客机和帧率范围未覆盖。

本次仅执行用户要求的发布检查，结果见 [publication-checks.json](publication-checks.json)：暂存 diff、Python/PowerShell 语法、JSON、大小/二进制/敏感信息、共享补丁复原、导航链接及远端回读。

## 沉淀的工作流

- [武器生命周期与攻击入口](../../../skills/ue5-weapon-workflow/references/thunder-hammer-lifecycle.md)
- [复制字段与短暂终止事件](../../../skills/ue5-save-load-replication/references/replicated-terminal-events.md)
- [已保存网格切线与回退模型](../../../skills/asset-model-workflow/references/saved-static-mesh-tangent-basis.md)

以上三份参考同时写入个人技能维护源，并在个人与工程 SKILL 入口添加路由。全局默认不主动测试和不跨会话协调的用户规则不变。
