# 野行上衣：皮革与布料改版

用户已确认 `SourceAssets/FieldRangerTop20261020/Design/FieldRangerTop_Concept01.png`，并授权建模升级现有绿色野行长袖上衣。物品 ID 继续为 `ue_field_sweater`，沿用现有装备槽、价格、防御、库存占格、骨架及动作。

## 款式与制作

橄榄色细斜纹布作为主体，深棕软皮用于肩胸轭片、低立领、肘外侧、前臂及袖口。新增遮盖门襟、斜向嵌线口袋、细包边和低矮黄铜按扣。第一人称袖身增加约 0.1–0.4 cm 的柔和褶皱与余量，袖口末端保持当前原生位置；身体背部加入浅活动褶。

皮革分区在三角形内按连续边界裁切，具有约 0.12 cm 的实体厚度；立领和领部连接使用约 0.15 cm 厚度。新增点的权重从对应原生衣服边界插值，内外层共用绑定；没有重新制作持枪、拉弓、攀爬或近战动画。

布料与皮革各有 2048×2048 BaseColor、Normal、ORM，使用 8 cm 物理尺度。斜纹纱线、皮革颗粒与浅凹凸来自独立的高度场，保留浮点高度源及烘焙用高模；法线为 OpenGL，UE 导入翻转绿色通道。材质保留流送，不使用额外视差或逐帧材质解析。

## 原生覆盖范围

- 第一人称 23 套：M4、AKM、QBZ191、ASH12、M16、M1911、DW715、A762、SVD、PKM、RuneSword、FrostSword、FrostArms、Axe、Pickaxe、DW715_l、DW715_r、M1911_l、M1911_r、Traversal、Bow、LMG201、Super90。
- 第三人称：Body、Jason。
- 第一人称低头身体：Owner_Jason，继续沿用原肩部连续分界；新隐藏材质索引为 6–11。

合计 26 份骨骼网格。第一人称沿用 `GarmentSleeveRepair20261018` 当前修复后的原生拓扑和绑定源。Body 保留其嵌入的可见皮肤与原生产皮肤材质；Jason 保留原身体覆盖合同。新增皮革层与衣身共用骨骼驱动，没有额外独立布料模拟。

三档骨骼 LOD 暂保留完整拓扑，优先保留袖口、内外层和细分片的对应关系；拾取与展示网格使用 100% / 55% / 30% 三档。这里是制作策略，未进行性能采样或动画验收。

## 文件

- `Tools/FieldRangerTop/`：当前来源捕获、PBR 烘焙、几何制作、导出、UE 保存与按物品发布脚本。
- `SourceAssets/FieldRangerTop20261020/inputs.json`：原引用、批准设计和各绑定源清单。
- `Authored/ue_field_sweater/*.json`：26 份完整几何、UV、法线、骨架与权重。
- `Exports/`：26 份原生 FBX；Body、Jason、Owner_Jason、M4、Bow 五份可编辑 Blend；独立装备图标场景。
- `Textures/`：六张 PBR 贴图及两个真实浮点高度源。
- `ue_field_sweater.png`：新模型制作的 320×320 透明装备图标。
- `/Game/Characters/ModularOutfit20260924/FieldRangerTop20261020/`：本次独立 UE 资产目录。

发布脚本只更新 `items.json` 和 `modular_outfits.json` 中该物品的外观字段与网格引用，保留其他装备和并行修改。新旧图标引用的兼容 PNG 同步更新，旧图与配置保存在本批 `Before/`。

## 状态

作者源、PBR、26 份原生 FBX、五份可编辑母版和装备图标已完成。26 份 UE 穿戴模型、拾取模型、展示模型及 UI 纹理均已保存，现有野行上衣配置已切换到新版本；`saved_assets.json`、`display_assets.json`、`published.json` 均记录完成。生产日志为 `materials-01.log`、`save-01.log` 至 `save-07.log`、`display-01.log`。没有修改 C++，无需重新构建原生模块。

本轮没有启动编辑器界面、试玩、自动截图或动画／游戏测试。穿戴、持弓持枪、第一人称低头和换装后的最终效果由用户试玩。
