# 蓝色法师手套

物品 ID：`ue_blue_mage_gloves`。与蓝色法师长袍、尖顶帽配套。首版概念图由内置 imagegen 生成，参考帽子的配色与材质；图稿已展示，未记录用户的外观验收。

- 设计图：`SourceAssets/BlueMageGloves20261019/Design/blue-mage-gloves-concept-v01.png`
- 完整提示词：`SourceAssets/BlueMageGloves20261019/Design/prompt-v01.txt`
- 模型、贴图与接入脚本：`Tools/BlueMageGloves/`
- 可编辑源及 FBX：`SourceAssets/BlueMageGloves20261019/Exports/`

## 版型与手部适配

蓝色细织物手背、深蓝薄皮掌心与指腹、银色星形和藤纹刺绣、低矮蓝宝石腕扣。采用全指和收束短腕口；指腹与指缝不增加硬质装饰，复用现有抓握和施法动作。

本轮从当前 `modular_outfits.json` 中的 `ue_field_gloves_black` 读取实际保存的手套网格，参考其完整手型、原生蒙皮、UV、柔软回折腕口与内壁。没有替换裸手母版或既有手套。对应原生绑定保存在 `Sources/`，制作后的新装备网格保存在 `Authored/`。

为与法师袍贴合，重叠腕口沿径向收薄 1.2 mm，向手掌平滑过渡；掌心、指腹和指缝的抓握包络保持原版。内外腕口共同变化，保留回折结构与对应权重。腕扣位于手背靠腕区域，采用同一小片表面的权重，不跨指关节。

Jason 的手指凸起、指间关节及腕部辅助骨权重保留。作者空间映射使用其对应命名祖先的坐标系，不删除修正骨、不把所有装备统一换成 M4 骨架。

## 材质与制作源

织物、皮革颗粒、缝线、刺绣与针脚以厘米尺度的同源表面场制作，栅格化到现有手套 UV 图集。图集法线通过物理高度及各三角形的 UV 尺度生成，采用 OpenGL 约定，UE 导入翻转绿通道。手背布料和掌面皮革分别设置色彩、细节、粗糙度与绒面遮罩。

第一人称图集 4096²，Body/Jason 图集 2048²；每组 BaseColor、Normal、ORM、Relief 四图。Relief 的 RGB 分别为高度、绒面遮罩、UV 岛内视差衰减，延续现有有界浅层视差材质方法，深度 0.06 cm，保留 mip 和纹理流送。腕扣金属与宝石分别使用套装已保存材质。

Blender 作者文件中包含原生绑定的游戏网格；M4 与 Body 另外保存实际位移后的 `HIGH` 表面源，分别约 33 万、35 万多边形，仅用于制作。游戏网格双手通常 27,758 三角形，独立单手 13,879，Body/Jason 29,416。高模不导入游戏。新装备使用三级 LOD；没有改旧手套的 LOD 或动作。

库存 PNG 为 320×320 透明底，只显示一只空手套。由新游戏网格、生产材质和独立松弛展示姿态渲染，未回写任何游戏动作。展示与掉落静态网格同源保存。

后续图标制作统一走[法师套装图标标准](blue-mage-set-inventory-icons-20261019.md)，保持单只构图，并将图标专用展示网格对准 UE 的固定捕获镜头。现有物品引用保持，掉落网格不随图标姿态调整。

## 当前适配范围

25 个配置适配组：Body、M4、AKM、QBZ191、ASH12、M16、M1911、DW715、A762、SVD、PKM、RuneSword、FrostSword、FrostArms、Axe、Pickaxe、DW715_l、DW715_r、M1911_l、M1911_r、Traversal、Bow、LMG201、Jason、Super90。每个适配组及所有实际源路径见 `inputs.json`、`manifest.json` 和保存回执中的 `aliases`。

新物品使用现有手套槽 3，独立 `appearance_family=BlueMageGloves20261019`，配方 `material` 留空以保留布料、金属、宝石三个材质槽。通用装备、存档、联机与 Leader Pose 路径继续复用。基础数值沿用参考薄皮手套，没有新增技能效果、稀有度或新动画。

## 后台制作和状态回执

`capture_sources.py` 读取当前实际装备，`author.py` 制作独立派生及腕口接口，`bake_atlas.py` 烘焙图集，`save_editable.py` 保存可编辑源、FBX 和正式图标，`save_assets.py` 通过现有 UE 批次互斥导入并逐件保存。源哈希用于中断后继续该批次。`publish.py` 在全部保存后精确增加新物品与装备配方，保留并行目录改动。

`editable_receipt.json` 为模型源导出回执；`saved_assets.json` 为实际 UE 包保存回执；`published.json` 为正式目录接入回执。本次没有新增 C++，不需要为资产制作额外编译游戏代码。

本次落盘完成：`glove-import-01` 通过已有编辑器桥返回成功，25 个原生适配组均保存了三级 LOD；图标纹理、展示和掉落静态网格均已保存。`publish.py` 已发布新物品及配方，覆盖当前 66 条注册源路径。未改变参考黑色手套、长袍或帽子的资产。

未启动游戏、PIE 或额外编辑器，也未执行动作、视觉或联机测试。设计图和正式物品图标属于本次制作交付；游戏内贴合、袖口交叠与握持效果由用户试玩。
