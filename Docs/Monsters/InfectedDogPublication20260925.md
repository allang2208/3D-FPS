# 感染犬：归档、技能沉淀与源码发布

2026-09-25，按用户要求整理本次完整感染犬制作链。当前角色为 `BP_InfectedDog`，模型与动作数据集位于 `/Game/Monsters/InfectedDog/MeshyV2`，三个奔跑槽位统一使用 `GodotRunNaturalV3`。用户已认可该跑姿可作为四足犬科模板；最新飞扑/索敌升级已后台编译、保存配置，尚未进行游戏测试。

## 本次发布范围

- 感染犬原生类、F6 入口、六维和三阶段感染；属性衰减为 5% / 30% / 50%，每秒按最大生命扣 0.2% / 0.5% / 1%，60/180 秒升级阶段。保存、恢复、状态面板、战斗公式和净化同步接入。
- 犬科预测飞扑、胶囊边缘咬击和突变体 3 追踪分支复用；仅感染犬默认开启，原狼行为保留。见 [攻击与寻路记录](InfectedDogHunting20260925.md)。
- Meshy 本地绑骨/口腔与目标骨架动作制作、Godot 原始 Gallop 直接适配、根单位修复、独立奔跑安装器，以及共享血迹材质的 HLSL/Coverage 修复。
- 个人与项目镜像的怪物 Skill、流体透明问题参考同步更新。其他会话的韧性重构、近战武器、地牢等未纳入本次源码提交；感染犬阈值初始化兼容当前共享韧性字段迁移的两种命名。

## 已归档内容

本机 `trash/infected-dog-retired-20260925/` 保留原相对目录结构：319 文件，343,734,373 字节。`manifest.json` 逐文件记录原路径、归档路径、大小、SHA-256、原因和替代入口；移动后逐项复核散列一致。该目录及其二进制不推送。

| 原目录/方案 | 归档原因与替代 |
| --- | --- |
| `SourceAssets/CanineGallop20260924` 与 WolfV3 内容/专用脚本 | 用户否决错位、穿模；改用实际 Godot 源直接适配 NaturalV3 |
| `SourceAssets/InfectedDog20260924`、`InfectedDogRealisticSkinV2`，相应 UE 候选和脚本 | 原狼换皮不能满足裸皮犬体型/表面要求，改用 MeshyV2 |
| `SourceAssets/InfectedDogMeshy20260924/FoxRunV1` 与 UE/专用脚本 | 后续改用 Godot 原始 Gallop，Fox 候选退出现役 |
| Meshy 失败四足 rig/web 分支、Diagnostics、网页操作和 API 调研快照 | 本地绑骨已完成，保留失败证据在归档；成功生成/重拓扑配方留在正式目录 |
| 本制作链 `.blend1` | 自动备份归档，可编辑母版仍保留 |

后台只读资产注册表记录显示上述 21 个 UE 候选没有组外引用，归档保留它们的组内依赖；未改正式 BP、Meshy 身体或当前动画引用。回读依据在本机 `Saved/InfectedDogPublication/asset_references.json`，本次未运行游戏。

## 正式重建依赖与顺序

保留 `Meshy/candidate01` 高模/PBR、`candidate01_quad50k`、`LocalRig`、`CompletionV2`、`GodotRunFitV2/Source`、`GodotRunNaturalV3` 与 hunting 安装回执。LocalRig 是后续口腔制作的输入，FitV2 是保留的回退版，均不当作废案。

1. 从本机恢复上述原始模型/PBR 与合法 Wolf 素材；`author_meshy_local_rig.py` 生成绑定，`complete_meshy_mouth.py` 补口腔。
2. `export_meshy_animation_sources.py` 读取已独立保存的 `CompletionV2/source_action_bindings.json`，导出源动作；`retarget_meshy_canine.py` 制作 21 个目标动作。
3. 后台执行 `install_meshy_completed.py`，缺失时直接创建 InfectedDog 原生类 BP，从正式 Wolf 动作合同生成数据集。无需恢复旧皮肤、旧 BP 或 trash。
4. `GodotRunFitV2/Source/wolf_quaternius.gltf` 为原始源，`sample_godot_gallop.py` 可重新采样；`author_godot_run_natural.py` 生成自然化奔跑，`install_godot_run_natural.py` 完成三个跑步槽位绑定。共用逻辑已从旧 Fox 脚本提取至 `install_canine_run.py`。
5. `install_hunting_upgrade.py` 保存追踪/攻击配置。共享血迹修复走 `repair_blood_stain.py`；全量重建也已更新 `author_fluid_polish.py`。

完整重建需要先恢复 Wolf 数据集、Animal Variety Pack、行为树和共享材质。二进制模型、纹理、动画、UE 包、DLL、外部软件与插件不随 Git 分发；Git 克隆不等于可直接运行的完整游戏。

## 素材与公开边界

Godot Gallop 来自 Quaternius Ultimate Animated Animals（CC0-1.0，来源记录见 NaturalV3 README），历史提交 `49cec1dd11d65295f43c737bac327de829cfd7b1`。其 CC0 不覆盖 Wolf/PROTOFACTOR 动作、Fab 包或 Meshy 生成体；后者沿各自来源/账户许可恢复，原始素材未纳入本次公开提交。退役 Fox 的 CC0 记录随候选保留在 trash。

本次只发布自有源码、制作配方、少量无凭据参数及文档。Meshy 任务响应、签名链接、浏览器资料、密钥、密集骨点采样、运行日志均留本机。推送前执行明确路径暂存、完整差异/大小/敏感信息/许可检查与远端回读；不附加游戏、渲染或玩法验收。

本轮整理修正的重建脚本与阈值字段兼容尚未重新构建/执行；上文后台构建是先前 hunting 接入的记录，不代表此次暂存子集独立编译验证。共享暂存区出现其他任务的 UI 文件后，本次使用独立临时索引组装提交，保留那批暂存内容。
