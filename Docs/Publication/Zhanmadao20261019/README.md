# 斩马刀、背嵬、赤霄与逐风 · 2026-10-19

本次发布覆盖本对话的斩马刀接入、标准图标、通用改造、唐刀两款刀身移植及群体判定、背嵬符文、赤霄双斩、逐风前进旋风和已完成的联机修复。其他枪械、战锤、法术、衣物、怪物、地牢及生产系统的并行修改保留在工作区，不随本次提交发布。

## 当前内容与制作入口

| 内容 | 当前效果 / 接入 | 制作与恢复入口 |
| --- | --- | --- |
| 斩马刀 | 双手长刀，刚体长度约 160.1314 cm 与镇岳一致；攻击距离 225 cm；基础间隔 2.04125 秒，已有实例迁移基础间隔 | `SourceAssets/Zhanmadao20261018` 的 `prepare_model.py`、`author_modules.py`、`install_assets.py`、`publish_catalog.py` |
| 通用件和图标 | 刀身、符文、护手、握柄、配重；沿既有方形灰钢底板、铆钉和内框标准 | `CommonModsV2`；基础 `author_inventory_icon.py` / `author_factory_icons.py` |
| 破锋燕翎 / 腾云游龙 | 唐刀与斩马刀共用机制：第三段分别为矩形群体竖劈 / 群体升龙，每目标每次收尾一次；说明补齐第三段 +40% / +30% 伤害及原有代价 | `TangDaoBladesV1`；`SourceAssets/TangDaoMeshy20261002/{YanlingBlade20261002,TengyunBlade20261002}/catalog_extension.py` |
| 刀面符文 | 按各刀身表面与走向独立拟合 | `RuneSurfaceV1` 的布局、placement HLSL 与材料安装器 |
| 背嵬 | `blade_2` 传说专属；金色行书“精忠报国”；武技伤害 ×1.5、武技判定范围 ×1.25，释放时金色剑气 | `BeiweiRuneV1`；`FrostSwordRunes`、`MeleeRuneVisual`、`BeiweiSwordTrailComponent` |
| 赤霄 | `blade_1` 传说专属；重击两次各造成完整重击伤害，计为武技；出手体力 ×2；攻速 ×1.15、物攻 ×1.1；红色剑气 | 刀身 `ChixiaoBladeV1`；动作 `ChixiaoDoubleHeavyV1` → `ChixiaoGripV2` → `ChixiaoShoulderV3`；玩法作者入口 `ChixiaoLegendaryV1/catalog_extension.py` |
| 逐风 | `blade_1` 传说专属；冲刺攻击变为持续前进旋风，保留冲刺速度，旋转结束或受阻停止；范围 ×1.2、物攻 ×1.1、旋风伤害倍率 +0.5；青色剑气 | `ZhufengBladeV1` 的模型、标准图标及 `catalog_extension.py`；`ZhufengCyanTrailV1`；`ZhufengDamageBonusV1` |
| 逐风第三人称 | 复用现用旋风三段，给去根转向的动作补上胸部整分支旋转；腿脚保持正常向前移动 | `ZhufengWhirlwindMotionV2`、`FPSBodySwordMotion`、`FPSBodySwordPose`、`FPSPlayerBodyAnimInstance` 接入差量 |

逐风需要冲刺攻击准备完成，沿用大旋风的等级、消耗和冷却；未学大旋风时以一级数值计算。倍率 +0.5 和青色剑气也作用于安装逐风时的主动大旋风。属性卡显示被动数值，特殊说明只保留动作、条件与代价。

赤霄使用独立武技时钟，两次触点分别去重；翻倍的是出手扣费，蓄力期间的每秒消耗不翻倍。第二刀左手抓握与右肩断口修订保留用户认可的整体刀轨。

## 联机接入与已有结果

旋风施放现在由服务端提交消耗和冷却，命中携带施放序号并使用服务端伤害／范围快照。群体命中通过每次施放的目标集合去重，不消耗枪械逐命中 token；眩晕、击退、符文效果和修炼由服务端结算。CMC 推进绑定已接受施放，锁定起手方向并限制累计距离，移动包先到时可等待下一次累计请求。死亡、换武器、退出和换图关闭授权。旧物品指针不跨档案替换使用。

[已有检查记录](Evidence/ZhufengNetworkReviewV1-review.json) 来自用户上一轮要求的排查：目录 18 项、原生隔离 38 项，均为 0 失败；Editor / Game 构建分别在 2026-10-19 15:46:49 / 15:47:15 成功。该夹具直接调用权威实现并做反射归档回读，没有真实 NetDriver、客机进程或地图 BeginPlay。不能据此声称真实双端、时延／丢包或画面验收通过。

本次整理只做归档、源码范围、补丁适用性、脚本语法与 Git 发布检查，没有重跑游戏或上述检查。`Evidence` 均为旧回执副本，来源与散列见 [evidence-sources.json](evidence-sources.json)。早期 `ZhufengBladeV1/delivery.json` 的未编译状态已由后续 Motion / Cyan / DamageBonus / NetworkReview 记录更新，不代表现在仍未完成编译。

## 共享源码的发布与恢复

独立原生文件、可分离的小文件、目录和制作脚本按原路径发布。34 个混合宿主的本轮修改发布为 `Integration/*.patch`；本机已接入，不要重复套用。

[integration-manifest.json](integration-manifest.json) 逐文件记录基线、结果和 UTF-8/LF SHA-256。基线由当前宿主逆向去除已审阅的本轮差量构成，保留其他并行前置；它不是 Git HEAD 的同义词。恢复前先取得本机 `SourceAssets/ZhanmadaoPublication20261019/Prerequisites/Before` 对应文件，核对散列后应用补丁；结果应匹配清单。完整混合宿主仅在本机保留，不公开夹带其他任务。

前置包含现有上挑权威与累计体力镜像、身体动画宿主、武技冷却恢复、技能检查宿主，以及它们依赖的项目系统。补丁中的上下文仅用于定位，不表示相关战锤、法术或枪械功能属于本次发布。公开树不是完整本机工程的独立构建副本；此前完整本机工程构建成功也不是公开子集构建证明。

目录发布限定 `ue_zhanmadao`、其材料映射与 Chixiao 身体片段；唐刀仅包含两款刀身的兼容、群体说明与代价。本轮改动不会替换其他工作区目录条目。

## 保留输入与退役

`ChixiaoShoulderV3/author_root.py` 读取 V2 Blend 和姿态，V2 又读取 V1；这些旧目录及原始 Meshy GLB、最终可编辑模型、认可概念、图标和输出 FBX 都保留。末次安装应以 ShoulderV3 为准，不能用 V1 重导入覆盖手腕／肩根修订。许可源、密集动作数据、模型及媒体的本机路径和散列见 [local-authoring-inputs.json](local-authoring-inputs.json)；已保存的正式资产见 [local-assets.json](local-assets.json)。

已完成的九个临时 AssetHost、明确失败／中止的尝试、过时目录备份、一次性编辑器探针及此次补丁应用临时副本进入 `trash/zhanmadao-retired-20261019`。作者脚本可重新生成所需宿主；正式 Content 未移动。恢复宿主不构成绕过共享批次互斥或覆盖已加载资产的授权。

[归档计划](archive-plan.json) 与 [归档回执](archive-receipt.json) 记录共 730 个文件、1,754,039,708 字节，移动后 SHA-256 一致。完整逐文件原路径、目标、大小、散列、原因与替代物保存在本机 `SourceAssets/ZhanmadaoPublication20261019/retired-files.json`；该清单散列随计划公开。

## 许可与技能沉淀

本次仅公开源码、配方、少量布局参数、来源散列与文档。Meshy 模型、字体／书法素材、UE/Fab 动作母版、贴图、图标、Blend、FBX、UE 包和密集姿态 JSON 不随源码再分发；恢复这些内容需要本机输入及相应许可。`trash`、构建缓存、原始日志和混合宿主前置保持忽略。

个人维护源与工程镜像已同步本轮增量：

- [武器配方与剑气](../../../skills/ue5-weapon-workflow/references/zhanmadao-legendary-blades.md)
- [持剑接触与第三人称旋风](../../../skills/ue5-fps-arms-animation/references/third-person-sword-contact.md)
- [武技回执与 CMC 顺序](../../../skills/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)
- [隔离夹具边界](../../../skills/ue5-debug-validation/references/authority-hit-fixture.md)
