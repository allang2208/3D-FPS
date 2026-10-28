# 高地长弓开发整理与发布

本批保存高地长弓模型接入、通用改造重平衡、远峰/穿云弓体、观峰 3–6 倍镜、山鸣/疾律传说弓弦、金色弦影箭与选定冲击音、阿尔卑斯 HUD、快速近战，以及最后两轮联机修复和浮窗精简。

## 当前口径

- 高地长弓 `bow_woodsteel`：固有有效射程 +50%，特殊性质仅此项及无声射击；详细浮窗删除“完美节拍”说明，机制保留。猎手长弓维持自身暴击被动。
- 远峰：最大飞行距离 +30%、完整箭矢伤害 +25%、拉弓速度 −25%、单箭/持续耗体 +40%，没有暴击伤害加成。穿云：最大飞行距离 +45%、暴击伤害 +75%、物理伤害 +10%、拉弓速度 −35%、单箭/持续耗体 +55%。
- 通用强拉力：物理伤害 +5%、穿心箭伤害 +30%、单箭/持续耗体 +50%；普通拉弓与穿心箭共用速度。游隼、磐木、细枝分别偏向快拉省力、远射重箭、腰射连射；精确数值以本目录目录快照为准。手制磐木已退出选择并有旧件迁移/材料退还。
- 疾律：被动节拍窗口 +100%；每层拉弓速度 +20%，5 层上限，6 秒。满层物理伤害 +20%、腰射扩散 −50%，成功射出手动箭即判节拍并刷新；未满层失拍、到期、换武器或死亡清空。山鸣：普通满弓箭命中存活敌人或训练靶逐次点亮，弦影箭不递归叠层。
- 观峰镜当前采用主摄像机 3–6 倍放大，圆形分划和外围显示同一场景；独立视模构图、平滑倍率和机械环同步。仅观峰不铺黑外围；所有高倍镜保留战斗 HUD。早期 PiP 文档是历史方案。

## 发布和恢复合同

`patches/` 与 [integration-manifest.json](integration-manifest.json) 保存本批源码/配置增量。公共宿主已含大量本机未完整公开的库存、身体与武器前置；这些补丁是定向集成材料，不能将补丁基线或裁剪内容写回当前共享工作文件。本批没有将其他在途开发整文件发布。

每份补丁记录规范化基线、结果、补丁及当前完整文件 SHA-256（UTF-8 去 BOM、CRLF 转 LF）。HEAD 基线指清单固定提交；`reconstructed prerequisite` 是当前文件只移除本批改动后构造的前置，不是历史 Git 提交。Before 基线已经移到归档清单对应位置。精确补丁应用/结果散列检查只证明增量可恢复，不代表干净克隆可构建。

先恢复 [弓系准备技能发布](../BowSkills20261027/README.md) 的穿心箭、魔法箭雨、元素/照明箭和资源/库存回执前置，再按本批依赖合入。弓 draw GUID 与取消/释放回执修改涉及双方 RPC/结构；服务端和客机必须同版。共享影子档、原生手臂、近战查询和经验 HUD 仍依赖完整本机工程。

`bows.json` 与 `bow-gunsmith.json` 是最终完整弓目录快照；共享目录只取 [shared-catalog-entries.json](shared-catalog-entries.json) 的具体 ID，按 ID 合并木工入口、配方和 `bowCadence`，不可覆盖其它条目。AlwaysCook 路径增量包含在配置补丁中。

## 制作链和本机资产

原始 Meshy GLB 来自用户提供的 Downloads 文件。正式包在 `/Game/Weapons/WoodSteelLongbow20261026/`，复用猎弓手臂、材质与快速近战动画。原创作者/导入脚本和提示词随本批发布；模型、FBX、BLEND、PNG、音频、UE 包、第三方插件与构建产物保持本机。恢复完整工程还需这些本机/备份资产，公开 Git 不是完整二进制备份。

- 正式高地弓体/接触和麻布/镜片 UV：根制作脚本、RepairsV2、HighlandV3；远峰由 FarPeakV4 + FarPeakIconV6，穿云由 CloudpiercerV9，镜体由 Scope3to6V11 制作。
- 山鸣实体弦 MountainEchoV13；V14 基础金光资源 → V18 爆炸 → V19 飞行。AlpineV23 的纹理/材质为当前山形 HUD；`ResonanceHUDRepair20261028/repair_materials.py` 是已保存 D3D12/SM6 材质接线修复记录，不能用 NullRHI 替代。
- 疾律 CadenceV1 借用 MountainEchoV13 实体弦接口与 AlpineV23 材质制作链。图案进入 buff 栏，中央沿用直观进度提示。当前参数以目录与 `CadenceString.h` 为准，旧设计文档不覆盖它们。
- 冲击音采用 SelectedB4；EnergyFusionV4 使用 BowSemanticV2 的 DSP 函数，所以保留该 helper。TannerSound 原音源为 CC BY 4.0，短气流层为 artisticdude CC0；来源、授权链接与修改说明随 CREDITS 发布。源录音和加工 WAV 不公开再分发。
- 快速近战 V8 的 `author_impact.py` 依赖 RecoverV7 → WristV6 → PalmV5 → ContactV4 → SightContact 的既有作者链；这批未把它们当废案。正式资源仍为 `/Game/Weapons/DarkBow20260925/QuickCombat20260926/A_Bow_QuickCombat`。

[asset-dependencies.json](asset-dependencies.json) 是本批目录/源码直接引用的资源清单，不是完整传递依赖导出。导入脚本存在本身不证明资产已导入。

## 归档与交付边界

[archive-manifest.json](archive-manifest.json) 记录 177 份退役候选、旧快照及中间发布补丁的原路径、trash 路径、字节数、SHA-256、原因和替代物；约 121.0 MiB。归档后散列全部读回一致。没有删除正式内容、存档、现有构建或其他开发文件。检查失败/成功回执和有效供体保留本机。

上一轮用户明确要求的检查：Game 与 Editor 基础目标均已构建；本次末轮隔离检查为表现 25 项和弓弦联机模型 44 项。具体历史证据见 [bow-presentation-network-review](../../Weapons/bow-presentation-network-review-20261028.md)；未进行真实主机/客机 socket、高延迟丢包、晚加入/重连、画面和声音验收。早期报告里的疾律旧参数不代表最终 6 秒/100% 配置。

本轮只执行授权的仓库归属、补丁重建、大小、敏感信息、许可、归档散列和推送检查，没有启动 UE、构建、玩法测试或验收。相关武器、UI、手臂 SKILL 已同步个人源和工程镜像。

从原工程使用独立索引发布，保留其他暂存和工作区；仅普通推送到授权仓库 main，推送后回读分支和旧引擎归档标签。
