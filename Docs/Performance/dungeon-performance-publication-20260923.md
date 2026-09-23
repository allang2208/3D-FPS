# 地牢性能优化整理与发布（2026-09-23）

用户已自行测试并反馈帧数改善。本次发布 HUD 重复刷新消除、只读 JSON 复用与轻属性查询、起始区旧灯调度、图标 mip 和重试预算、纹理池预算，以及对应的资产制作方法和 SKILL。保留已恢复的硬件光追、Lumen 与原有昼夜配光。

## 废案归档

本机 `trash/dungeon-performance-rejected-20260923` 保存 25 个文件，共 130,562 字节：13 个光追剔除／光栅补偿／恢复专用脚本，2 份撤回方案说明，7 个已弃用补光预设，以及3个已用完的编辑器交接／固定会话批次脚本。清单记录原路径、新路径、大小、SHA-256、归档原因与替代入口；移动后逐项散列一致，见 [清单](../AssetArchives/dungeon-performance-20260923.json)。

归档前离线扫描 21,518 个非目标资产包名称表及 Source、Config、ColdSteelData，没有发现 RasterProfiles 引用，扫描错误为 0。整理期间已有 UE 进程启动，因此另经现有桥批次互斥读取 AssetRegistry 与内存对象：7 个目标均无外部引用、未加载且没有待保存修改，随后在同一互斥批次内移动。没有启动、关闭或重启编辑器。

有用的原文件备份与制作回执保留本机：`Saved/RayTracingRemoval20260923`、`Saved/LightingRestore20260923`、`Saved/SlateStall20260923`，以及 `SourceAssets/DungeonPerformance20260923Batch/Before`、`Receipts`。它们用于来源追溯与按项恢复，不作为可直接覆盖当前工程的整目录回退方案。

## 发布范围与恢复

当前 Git 根目录为 `D:/FPS3D/FPSGAME`，目标为 `https://github.com/allang2208/3D-FPS.git` 的 `main`，采用普通非强制推送。共用文件按本次具体差异暂存；保留其他任务的地牢奖励、冶炼、武器改造、技能等改动，不把它们夹入性能提交。

Git 发布源码、参数、制作与按需采集脚本、性能记录、归档清单及技能文档。uasset／umap、已许可第三方内容、二进制、日志、完整 trace、原文件备份和 trash 不公开。新克隆需合法本机 Content 才能恢复完整工程；资产制作步骤见 [作者说明](../../SourceAssets/DungeonPerformance20260923Batch/README.md)。楼梯导入脚本主体仍属于独立任务，本次只发布其 Nanite 修改补丁；本机对应导入器已经修改。

资产保存与后台构建结果沿用 [完成记录](dungeon-performance-completion-20260923.md) 的历史证据；本次整理仅检查归档、提交范围、格式、依赖入口和敏感信息，没有启动游戏或重新进行性能／画面测试。用户体验反馈与量化收益分开记录，没有同条件优化后采样，不填提升百分比。

推送前逐项核对 57 个暂存文件与本批清单、完整差异和 `git diff --cached --check`，检查 6 个 Python 脚本语法、2 个 PowerShell 脚本语法、JSON 结构、公开文档链接、文件大小和凭证模式。未发现二进制／授权素材载荷或实际凭证；修正性能 SKILL 中一个已退役的 MCP 文档链接。上述是仓库发布检查，不是新一轮编译、游戏测试或性能验收。

## SKILL 沉淀

[性能开发约束](../../skills/ue5-performance-packaging/references/fpsgame-performance-development.md) 统一维护 HUD 重复工作、缓存失效与容量、旧灯生命周期、几何制作、纹理预算、图标等待和真实性能归因。性能、C++、UI、PCG、武器、天气、技能魔法及 UE 入口技能均可到达，并同步个人技能镜像。制作回执仅能续接对应资产版本；后续重导不能凭旧回执跳过制作。
