# V7 裸手、手套与衣物：发布和恢复

本轮整理发布用户认可的 V7 裸手默认方案、模块化换装组件、贴合手套／衣袖制作链及标准 SKILL。源码与资产接入来自现有完成工作，本轮不重新构建或运行游戏；手套、衣袖的制作完成不代表所有动画已验收。

## 公开与本机边界

- 公开：模块化外观组件及必要角色／全身装备接入、五件装备目录、`modular_outfits.json`、作者工具、说明与 SKILL。
- 原生骨架、绑定、密集顶点／权重 JSON、导入回执、贴图、Blend／FBX／uasset 及下载素材包留本机，不因文件是 JSON 或衣服来源为 CC0 就公开派生数据。`.gitignore` 对两个 ModularOutfit 作者目录只放行说明文件，工具放 `Tools/ModularOutfit`。
- MakeHuman 衣服／手部及皮肤素材的来源记录留在 `SourceAssets/ModularOutfit20260924/Donor`。派生模型同时含原武器／手模数据，公开制作方法不代表这些源资产获得再分发许可。
- 共享文件只提交本轮相关片段，保留其他武器、技能、性能、建筑和 UI 等并行工作。没有为整理清空或重置工作区。

## 本机恢复顺序

1. 恢复已有合法的各武器、工具、剑、施法、攀爬视模及其原生骨架、动作和材料。V7 已将裸手写入 20 个基础视模的原手臂区域；恢复旧枪械包可能重新带回手套，不能只恢复独立裸手资产。
2. 恢复 `Content/Characters/ModularOutfit20260924`，尤其 `BarePalmV7`、`FittedFieldGlovesV1`、`FittedSleevesV1`、共享 Materials、Pickups，以及仍被 Body 使用的 NativeSkin／Profiles。恢复 `Content/ColdSteelData/Icons/ModularOutfit20260924` 库存图标。
3. 保留 `BarePalmV7/OriginalSources`、`OriginalGloves` 和作者目录 `NativeDefaults/Packages`：分别提供原生绑定与原版手套恢复件、原磁盘包。它们不是废案；不拿整包旧武器覆盖后续枪体改动。
4. 若需重建，恢复 `SourceAssets/ModularOutfit20260924` 和 `ModularOutfit20260925` 的实际输入与最终可编辑源。V7 仍依赖 V3 顶点对应、V4 表面数据、V6 腕臂和原生骨架导出；当前衣袖还读取 `FittedSleevesV1/M4_shirt_before.json`，这个带 before 的文件是制作输入。
5. 按 [工具入口](../../Tools/ModularOutfit/README.md) 先保存资产再更新对应配方。当前 `native_bare_arms=true` 表示基础模型已经裸手化；全局历史 `native_bare_hands_default=false` 并不代表这些基础模型仍戴手套。无需重开旧候选开关。
6. 只进行任务必要的后台构建、导入和保存；不因恢复而自动打开编辑器或运行游戏。源码仓库单独克隆不是完整可运行内容备份。

旧 `register_equipment.py`／`register_native_skin.py` 保留供初始链恢复，但直接重跑会覆盖后续配方。新增款式只更新自己的物品／profile；不能丢掉 `native_bare_arms`、原版手套恢复路径和 Fitted 装备引用。第三人称 Body 和未来联机观感分别处理，不能由第一人称完成推断已经验收。

## 归档

已将 69 份存在对应正式 Blend 的 `.blend1` 自动备份，以及两份已完成的一次性结束 PIE／Live Coding 文件移入本机 `trash/modular-outfit-retired-20260925/`。未删除源内容，没有移动任何正在使用的 UE 资产。

[71 项清单](modular-outfit-retired-manifest-20260925.json) 记录每项原路径、trash 目标、大小、SHA-256、原因、保留替代物及移动后散列确认。trash 实体不上传 Git。旧目录、候选名或 before 后缀本身不能作为废案判据；当前依赖、合法来源、正式可编辑源及关键失败对照继续保留。

## 标准与未测试范围

[第一人称手套与衣物标准](../../skills/ue5-fps-arms-animation/references/first-person-equipment-workflow.md) 同步个人／项目技能，记录装备贴合裸手、原生骨架派生与动画复用、局部接缝、覆盖编号、后台保存和布料边界。旧作者入口已标明历史状态及当前入口。

当前玩家衣服没有 Chaos 布料；巫婆经验仅作为以后宽松衣料的接入方法。保留衣袖原肩端 LOD 简化警告与本轮未进行运行验收的说明。整理只做用户要求的归档和推送检查，不追加游戏、动作或性能测试。
