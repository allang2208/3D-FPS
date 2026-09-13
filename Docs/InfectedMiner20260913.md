# 感染矿工：恢复原始工具动作

2026-09-13。用户拒绝 CMU 02_07 挥击后，改从工程已经导入的 Easy Building System V10 原始工具动作重建。使用 UE 5.8 自带 IK Retargeter；不在旧自编攻击或 CMU 片段上继续调整人体关键姿态。

## 动作与制作入口

源目录为 `/Game/EasyBuildingSystem/Mannequin/Animations/`：

| 状态 | 原始资源 | 原始时长 |
|---|---|---:|
| Idle | A_Mannequin_Axe_Idle | 79/30 秒 |
| Walk | A_Mannequin_Axe_Walk | 31/30 秒 |
| Attack | A_Mannequin_Axe_Act | 65/30 秒 |

保留原始全身动作和 1 倍节奏，采用引擎的自动骨链定义、精确同名骨链映射、目标参考姿态对齐与 FK 重定向。与 Epic 自动批量重定向流程一致，关闭额外的 IK Solve。手指局部姿态从已认可的 `AuthoredChopFinal/A_Miner_Idle` 第 0 帧复制；不改网格、绑定、权重或重做抓握。

原始斧击为工具挥砍，并非本任务新录制的单手矿镐动捕。`A_Mannequin_PickAxe_Act` 也已导出留作源参考，但本次不采用其双手举过头顶的采矿动作。源姿态和人体比例适配后的观感由用户试玩判断；不把源文件存在或编译成功称为动作观感通过。

新资产目录：`/Game/Monsters/InfectedMiner/EBSDefault20260913/`。可编辑重定向器为 `RTG_EBS_Default_Miner`，两套 IK Rig 同目录保存。生成的三个动画为 `A_Miner_Default_Axe_Idle`、`A_Miner_Default_Axe_Walk` 和 `A_Miner_Default_Axe_Act`。

伤害窗口按原始向前挥动阶段改为 11/30–17/30 秒（约 0.367–0.567 秒），不再使用 CMU 的 1.50–1.75 秒。派生动画移除 EBS 自带的 Notify 轨道，不调用原素材包角色专用的交互、伤害或音效事件。仍由已有权威战斗时钟执行，伤害 24、攻击范围 150cm、打断/死亡取消和一次命中合同保持原实现。窗口的视觉对应关系尚未经本轮试玩。

## 模型与免费矿镐

身体、160 骨、成熟前臂和手、PBR 材质、Physics Asset 使用已认可的 `/Game/Monsters/InfectedMiner/AuthoredChopFinal/SK_InfectedMiner`。现有十字镐暂留，木柄 0.96m、镐头跨度 0.72m。

用户提供的 [Orphans of the Great War 道具包](https://www.fab.com/listings/b78b786a-1a05-49c9-af7c-5487ced7fbb1) 已下载，其中是木柄斧头，未找到十字镐，因此不替换成斧头。

按用户随后要求找到免费的 [Basic Pickaxe — REAL DEDICATED](https://www.fab.com/listings/46ea08b2-1947-40f8-b1e7-f1254d49a912)。2026-09-13 官方页面显示 Free，列有 PBR、FBX、UE、Unity、Maya 等格式。浏览器页面加载超时，本轮尚未取得模型及贴图，也未接入，不能写成已替换。免费不等于可公开再分发；本任务 Git 不包含商店原始资产或派生二进制。

## 重建与交付

1. `Tools/InfectedMiner/export_default_tools.py`：从 UE 导出原始 EBS 工具输入，放入 `SourceAssets/InfectedMiner20260913/Reference`。
2. 编译原生 `FPSGAMEEditor`，提供 `ApplyAcceptedGrip` 资产制作函数和新接触时间默认值。
3. `Tools/InfectedMiner/rebuild_default_tools.py`：原生 IK 重定向、固定已认可的手指抓握、导出 FBX，并保存现有 `BP_InfectedMiner` 的模型、三动画和伤害窗口引用。
4. Blender 执行 `Tools/InfectedMiner/package_default_tools_blend.py`：把 UE 烘焙结果接回已认可的可编辑模型，输出 `SourceAssets/InfectedMiner20260913/Delivery/InfectedMiner_Editable.blend`。只替换动作数据。

原始网格导出使用 `-AllowCommandletRendering -RenderOffscreen`；不能用 `-NullRHI` 导出带预览网格的骨骼 FBX。重定向脚本只导出骨骼动画，关闭 `export_preview_mesh`，可使用 `-NullRHI`；模型网格来自已认可的源文件。三个 FBX 与本轮 `rebuild.json` 放在新的 Delivery 目录；旧 20260912 目录保留历史，不用旧打包脚本覆盖。

试玩仍使用村庄 `/Game/GameMaps/L_Normandy_FPS_Test` 内原 `InfectedMiner_Village_01`。无需另加怪物或重存整个地图。打开旧游戏或编辑器的用户需重启以载入新模块和资源。

原生 `FPSGAMEEditor` 构建完成，日志为 `Saved/InfectedMiner/build-default-tools.log`；UE 制作与接入日志为 `Saved/InfectedMiner/rebuild-default-tools-final.log`。本轮只完成制作、导出、接入及必要构建，不运行测试、不渲染预览。旧 CMU/KayKit 的验收记录属于被拒绝的历史版本，不能用作本轮结果。
