# 服装、帽子与两款腰带源码发布（2026-10-25）

本次整理覆盖腰部衔接、ST6 贝雷帽及裤靴细化、工装夹克与奔尼帽、户外工作套装、运动帽、战术弹匣腰带和右侧皮革箭袋腰带。发布原创制作工具、文本配置、可独立提取的运行时代码和技能经验；完整模型与 UE 资产继续保存在本机。

## 当前制作入口

| 内容 | 入口 | 有效本机源 |
| --- | --- | --- |
| 扎腰／裤靴衔接 | `Tools/GarmentWaist/run.ps1`、`policies.json` | `SourceAssets/GarmentWaist20261023`，保留 Read、Fits、Before 与回执 |
| 酒红贝雷帽 | `Tools/ST6Beret` | `SourceAssets/ST6Beret20261023/SurfaceV2`；作者和贴图脚本默认已改到此目录 |
| ST6 裤靴细节、背包图标 | `Tools/ST6LowerDetail` | `SourceAssets/ST6LowerDetail20261024`；ST6LowerSet20261018 仍是有效上游输入 |
| 工装夹克／精修奔尼帽 | `Tools/WorkwearSet/run.ps1`、`finish_assets.ps1` | `SourceAssets/WorkwearSet20261024`；奔尼帽继承 FieldHat 作者合同 |
| 户外工作套装数值 | `Tools/WorkwearSet/publish_outdoor_effects.py` | `SourceAssets/OutdoorWorkSet20261024`；五件穿齐，动作消耗 ×0.85、移动 ×1.10、食水自然消耗 ×0.75 |
| 炭灰运动帽 | `Tools/SportsCap/integrate.ps1` | `SourceAssets/SportsCap20261024`；只接入帽子，没有追加运动套装收益 |
| 战术弹匣腰带 | `Tools/TacticalMagazineBelt/integrate.ps1` | `SourceAssets/TacticalMagazineBelt20261024`；换弹 +2.5%，每级 +0.5 个百分点，15 级 |
| 右侧皮革箭袋腰带 | `Tools/LeatherQuiverBelt` | `SourceAssets/LeatherQuiverBelt20261025`；搭箭 +50%／拉弓 +5%，每级 +2／+1 个百分点，15 级 |

腰带与插槽分别按 Jason／Kaitlin 原生身体和实际 ST6 裤装适配。箭袋为材质位移驱动的轻微惯性摆动，当前上限 2 度／2 cm；五支现有木箭只是 Bow 武器表现下的装饰，不是额外弹药仓。开放帽保留整个头发 groom，闭面钢盔保持独立覆盖规则。

## 源码与共享文件

[source-scope.json](source-scope.json) 记录精确配置键、直接合入的消费者及补丁基线；[publication-manifest.json](publication-manifest.json) 列出实际发布文件和 Git blob。暂存候选从当时索引生成，没有覆盖共享工作文件。

四份 ColdSteelData 配置随消费者发布：`items.json`、`source-combat-items.json`、`player_body.json`、`modular_outfits.json`。原有装备只更新对应外观或套装字段；不夹带其他任务的武器、背包、食物和技能配置。裤腰解析器的实际裤网格优先、物品映射次之、默认回退最后已在公开基线中。

直接源码包括腰带槽发现／缓存／远端换装、箭袋生命周期、强化上限与预览、搭箭时长快照、旧实例数值和外观迁移、掉落物收到物品复制后恢复已收到的物理状态，以及现有动作的户外套装成本入口。公共基线中的奔跑旧提前 return 一并移除，以使成本路径可达；所有修改仅进入所属索引差分。

`Integration/` 中是仍依赖混合宿主的独立接入差分，不是已并入公共运行模块的完整功能：

- 持续重击蓄力、升龙斩新武器分支、单手刀的成本乘区，依赖对应尚未独立发布的重击／单手刀实现。公共基线已有的普通攻击、升龙和格挡成本另已直接接入。
- 弓远端采样乘 `StageActionRate`，依赖当前本机 LightningHaste 的阶段时钟；不能在没有该成员与时钟推进的公共基线上盲目应用。
- 户外套装的新摘要表和路由，依赖另一项套装进度 UI。公共基线保留目录说明展示。
- `QuiverBeltAudit.cpp` 与两份入口补丁依赖当前本机 `BowSkillTrainingAuditCommandlet` 的测试设施和 friend 声明，恢复时放回 `Source/FPSGAME/Skills`。不自动编入本次公共模块，也不自动运行。

补丁的 `before_sha256` 是该条修改回退后的本机宿主文本散列。各补丁独立描述相应改动，其他补丁可能已存在于上下文；不是可不加判断顺序套用的补丁栈。恢复时先确认宿主依赖，再按功能整合，不能覆盖整份源码。

本机 GarmentWaist／Workwear 的最新入口还会调用另一个任务的 `Tools/BackpackFit/run.ps1`。该任务未在公共基线发布，本次公共制作入口仅保留服装所属步骤，不夹带背包任务；本机原入口及其后处理保持原样。

## 恢复依赖与许可

需要已许可的 Jason／Kaitlin 原生身体、头部与权重，既有 GarmentFoundation、BlueMageRobe 作者工具及原生服装源、V7/V9 手臂，当前 ST6 裤装，FieldHat 头部输入，以及现有 Bow 木箭资产。保留各 SourceAssets 的 Inputs、Read、Before、Authored、Delivery、Exports、Textures 与保存回执，不以运行时网格反向导出替代作者源。

战术腰带 `Delivery` 是外部缓存的目录联接，位置记在本机 `storage.json`；未移动或展开归档。`Content` 当前恢复目录亦属于有效生产数据，未作清理。皮革箭袋已经恢复并完成保存，旧 Content 缺失阻塞记录归档后以当前 `published.json` 为准。

`Tools/TacticalMagazineBelt/ReviewPlugin` 仅包含本任务编写的外置诊断插件源码。按需构建到独立输出并显式传给 `run_review_network.ps1 -Plugin ...`；不安装到正式项目，不发布编译产物。该脚本仅供用户明确要求对应联机检查时执行。

公开 Git 不包含原生身体衍生的密集几何／权重 JSON、Blend／FBX／GLB、贴图、图标、字体副本、UE 包、日志、缓存或 trash。工具中的 `/Game/` 路径是恢复合同，不表示资产二进制已上传；公共源码不能替代本机完整工程。

## 归档与历史检查

[archive-manifest.json](archive-manifest.json) 逐文件记录原路径、目标、大小、SHA-256、原因及替代物。34 个制作废案文件及 1 个遗留 Git 锁，共 232,017,578 字节移到 `trash/Equipment20261025/<原相对路径>`，移动前后核对哈希一致。包括贝雷帽首版输出、箭袋两份旧 `.blend1`、已被 Editor/Game 完整构建替代的 Live Coding 助手、已解除的阻塞记录及 Python 缓存。有效 Before 输入与诊断失败记录未按日期粗略归档。遗留锁为空文件，超过 15 小时未更新；独占读写打开并保持句柄后归档，未修改索引内容。

历史状态见 [delivery-state.json](delivery-state.json)。箭袋最近授权检查记录为 43 项目录／源检查、64 项隔离检查及 Editor/Game 构建；其中修复了客机旧腰带元数据迁移和远端弓阶段时钟。没有建立 UDP 连接。战术腰带此前有独立的 13 阶段、24 份双端状态记录；这不覆盖后加的强化、箭袋或未来修改。

本轮只做整理、技能沉淀和推送前的暂存范围、依赖、敏感信息、体积、空白及配置发布核对，没有启动 UE／游戏、重新构建或追加玩法验收。模型动态穿模、运动观感、箭袋真实双端传输、跨机重连和打包版本仍保留原验收边界。
