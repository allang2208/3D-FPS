# S12K 制作、联机修复与发布 · 2026-10-19

本轮整理本对话的 S12K 枪体、通用改造、12 发弹匣、20 发传说大弹鼓、专属后托、开火声音、左手动作、第三人称及联机配件清单修复。其他武器、怪物、衣物、生产工具与性能任务的并行修改不在本次提交范围。

## 当前制作与恢复入口

| 内容 | 当前本机输入 / 作者入口 | 运行接入与恢复边界 |
| --- | --- | --- |
| 枪体封闭与材质 | `SourceAssets/Saiga12KClosure20261018/Authoring`；`Tools/Saiga12KClosure` | 当前 `Saiga12K/Detail20261018/SK_Saiga12K_Manny`；Closure 私有材质；原生手臂及机械绑定保留 |
| 共用件 | `Saiga12KCommon20261017/{inputs,sources}.json` 与 `Tools/Saiga12KCommon` | 分槽位拟合，不以 AKM 原高度替代实际护木接触 |
| 12 发扩容匣 | Closure 的 `ext12.json`，前置 `Saiga12KMagazine20261017/Authoring` | `Detail20261018/SM_Saiga12K_Ext12` |
| 12k 大弹鼓 | `Saiga12KDrum20261018`，`Tools/Saiga12KDrum`；认可 V02 概念 | `Drum20261018/SM_Saiga12K_Drum20`；圆形端面朝枪口，20 发，装填 +75%、开镜 +10%，传说专属 |
| S12K撞火枪托 | `S12KStockReference20261018`，`Tools/S12KStockReference` | 稳定 `saiga12k_bump_stock` ID 和 SpecialStock 资产路径；射速 +25%、腰射随机扩散 −25%、后坐力 +10%，特殊专属 |
| 声音 | `Saiga12KAudio20261018/provenance.json`，`Tools/Saiga12KAudio` | 原 game-dev 开火 WAV 原样复用；消音沿用 CommonShotgun 的 Super90 Suppressed |
| 检视/空仓回握 | `Saiga12KInspectClearance20261018`、`Saiga12KReloadReturn20261018` | 六份私有配置；ReloadReturn 更新 vertical/canted/prism 的两个 empty 分支 |
| 共振握把与整臂 | `Saiga12KResonance20261019`，`Tools/Saiga12KResonance` | 当前 `SM_Saiga12K_angled` 与 `DA_angled`；约 2.15 cm 下移、真实承重座；保持手指局部姿态和机械接触 |
| 第三人称 | `FPSBodyRifleHold`、`FPSBodyRifleStockContacts`、`FPSPlayerBodyActions` 接入差量 | 使用实枪轴向/后托接触；F6 本地瞄准采样游戏相机，远端继续使用权威控制视线 |
| 联机配件清单 | `Saiga12KAttachments`、`Saiga12KMagazineAssets` 与 Tactical/BodyEquipment 差量 | 卸下件清空 mesh 引用；S12K 捕获前按资源/插座/变换稳定排序，保留实例/schema/租约校验 |

枪体前置链为 Original → Refine → Surface 的部件表 → Detail 可编辑模型 → Closure。`Saiga12K20261017` 原始几何/岛、`Saiga12KMagazine20261017` 弹匣源、Inspect 数学脚本与稀疏轨迹函数、InspectClearance 的运行采样输入仍在使用。PKM GripLayer56/ArmHinge55、AKM 动作、V7/V9 手臂及 WeaponSurface 是独立许可依赖，不属于本次废案。

动作最后安装顺序：六套 InspectClearance 配置 → ReloadReturn 三套空仓增量 → Resonance 的 angled 配置。旧安装器用于前置重建，不能在当前正式资产上随意重跑以覆盖末次修订。模型接入、生成和测试脚本都不因发布而自动执行。

后托旧形状已退役，但 `Saiga12KSpecialStock20261018/Receipts/surface-install.json` 保留资产归属凭据。缺失资产的初次创建入口为 `Tools/S12KStockReference/create_assets.py`，已改为读取当前参考图模型；已有资产使用 `install_revision.py`。初次创建入口不覆盖已有网格。所有后台保存仍走共享批次；已有编辑器保留，通过现有桥操作。

## 公开源码范围

独立 S12K 源码、作者/导入脚本、S12K 目录配置、Cook 路径、当前预加载候选与技能资料放在原路径。公共角色、武器、第三人称和检查宿主中的本轮改动以 `Integration/*.patch` 发布：本机已全部接入，不要再向当前工作区重复套用。

这些公共文件还含未公开的其他功能前置。`integration-manifest.json` 记录每个目标的基线来源、UTF-8/LF SHA-256、结果散列及本机恢复路径；捕获提交是追溯点，不代表每个补丁能直接套在它上面。恢复时先取得列出的宿主前置，再应用相应补丁。补丁的本机基线/结果保存在 `SourceAssets/Saiga12KPublication20261019/Prerequisites`，不公开整份混合宿主。

公开树不是完整本机工程的可独立构建副本。特别是第三人称/网络检查类需要既有 `ShotgunAttachmentAuditCommandlet`、`ShotgunWireAudit` 与技能网络检查宿主；相关前置已有其他发布记录。不能用本机完整工程的构建结果冒充本次公开子集的独立构建。

模型署名见 [源模型许可说明](source-attribution.txt)：TastyTony 的 Low-Poly Saiga 12k 为 CC BY 4.0，修改包含轴向/绑定/封闭重建和材质替换。本次不发布第三方模型、手臂、动作、母材、原音频、图标、密集几何/蒙皮/姿态 JSON、Blend/FBX/UE 包或 API 凭据；它们及当前重制输入留在本机。作者脚本不会重新授予所引用媒体的再分发权。

## 退役与依赖

[归档计划](archive-plan.json) 逐组记录原因、替代物、文件数量和字节数；[归档回执](archive-receipt.json) 记录移动后散列核对。完整逐文件原路径、目标、SHA-256、原因/替代物在本机 `SourceAssets/Saiga12KPublication20261019/retired-files.json`，其散列随计划公开。所有废案进入 `trash/saiga12k-retired-20261019`，没有删除正式 Content。

归档包含旧后托、被否决的横向弹鼓概念、失效的一次性关闭/独立保存命令、修订前备份、完成的临时隔离宿主/缓存和明确失败的检查尝试。Content/Config/Plugins 目录联接没有被递归遍历；移动的是临时宿主中的联接，不是联接目标。仍被模型和动作读取的老目录输入及用于比较的报告图片保留。历史报告中旧备份/失败尝试路径可通过归档清单找到；当前重制输入路径保持有效。

五个仍用隔离宿主的常用保存入口改为受原有互斥保护的正式 `FPSGAME.uproject`。其余只用于当次授权例外的脚本移入归档；过去的例外许可不是未来绕过互斥的通行证。

## 已有证据与本次边界

`Evidence` 保存的是之前用户要求检查时取得的结果，来源映射见 [evidence-sources.json](evidence-sources.json)：

- 47 项目录/包依赖、25 项隔离原生检查、145 项第三人称检查均为 0 失败。
- 本地真实 UDP 主客机检查 12 个阶段通过；两端各设置 60 ms 延迟和 5% 丢包，首客机/新客机各 6 阶段。包含仅客机试装历史、弹鼓/后托/瞄具/消音组合、检视、空仓回握、租约失效和恢复换件。接收握点最大差约 .0051 cm。
- 原生检查直接调用/采样动作，不是人工鼠标与 CMC 移动验收；新客机连接不等于同一玩家档案重连。公网、实际伤害目标、画面和听感仍由用户体验。
- Game/Editor 的此前构建成功记录在 network-review 中。此次仅执行依赖整理、归档散列和 Git 发布检查，没有重新构建、启动 UE、运行游戏或再次验收。

技能资料同步到个人维护源和工程镜像：[枪体/接口](../../../skills/ue5-weapon-workflow/references/saiga12k-production.md)、[左手/回握](../../../skills/ue5-fps-arms-animation/references/saiga12k-grip-and-return.md)、[联机清单/方向](../../../skills/ue5-save-load-replication/references/saiga12k-presentation.md)。
