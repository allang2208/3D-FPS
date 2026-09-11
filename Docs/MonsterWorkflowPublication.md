# 怪物工作流整理与发布（2026-09-11）

本次补齐怪物行为开发阶段：定义行为触发与退出、分配 Behavior Tree/Blackboard/执行职责、明确打断优先级、验证导航、接入单个怪物并回归其他怪物。个人与工程 `ue5-monster-workflow` 同步；手脑案例文首先说明当前 V07、NavMesh 和布娃娃已通过基线，早期失败只用于追溯。

## 归档

已确认退役的拼接脸嚎叫 `SourceAssets/HandBrain20260910/howl_v01` 和一次性 `Tools/MonsterAI/fix_test_controller.py` 移至 `trash/monster-workflow-20260911/`，保持相对目录。共 108 文件、1,171,170,108 字节；移动前验证绝对范围，逐文件记录 SHA-256 并在移动后核验。清单见 [归档索引](MonsterWorkflowArchive.json)，本机 trash 另存同版 manifest.json。

替代分别为 `howl_rebuild_v02` 的同一面部重建和已包含实例控制器设置的 `Tools/MonsterAI/install_ai.py`。当前模型仍依赖 hunyuan_v01、hunyuan_attack_source_v01、howl_rebuild_v02、death_v01 以及后续材质/雕刻输入，因此这些目录保留。未确认废弃的参考和重建输入不因文件名较旧而删除。

## 发布范围与恢复

发布怪物 C++、相关 AI 导航模块配置、真实枪声感知调用、AI/手脑工具、怪物技能及工作流说明。角色主文件的其他枪械变更不随本次提交。源码基线的资源恢复遵循 [AssetSetup](AssetSetup.md)。

本机二进制需要保留 `Content/Monsters`（含 HandBrain/SurfaceV07、AI 树/控制器/受击动画）、`Content/ZombieFemale`、`Content/ZombiSkinMaterial`、村庄及 `/Game/Tests/MonsterAI/L_MonsterAI` 地图，连同 ExternalActors/ExternalObjects；作者输入位于 `SourceAssets/HandBrain20260910` 和原始 Y 盘参考目录。当前发布不上传原始模型、贴图、声音、Fab 资产、uasset/umap、日志或 trash，不构成完整素材远程备份。

验证沿用本日 15:49–15:52 实际运行结果：AI 16/16、护士 15/15、手脑 30/30，见 [AI 工作流](MonsterAIWorkflow.md)。本次整理不修改玩法规则；另外检查技能格式/链接、Python 语法、归档散列、发布文件大小与敏感信息、暂存差异。上述历史运行结果不写成此次重新试玩。
