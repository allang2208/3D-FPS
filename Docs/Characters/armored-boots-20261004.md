# 灰钢铠甲靴

用户在本对话生成单靴概念图后要求继续构建。独立装备 `ue_armored_boots`，鞋靴槽 `13`；不替换现有系带皮靴或休闲鞋。

## 造型与制作

- 参考：`SourceAssets/ArmoredBoots20261004/Concept_v1.png`，提示词同目录留档。单张参考未显示的后侧与内部为本轮设计，不称精确扫描还原。
- 前护胫沿小腿收腰，中央浅脊、膝下弧形上口、实体卷边；下接两段活动叠片。
- 脚背五段叠甲、圆头钢鞋头、左右护踝和后跟护片；皮革在屈曲接缝与后侧外露，两个外侧金属扣固定后侧皮带。
- 靴筒具有外层、翻口和内壁，鞋底有独立皮革层、沿条和粗缝线。甲片厚度、倒角、铆钉、扣环均为实体几何。
- 作者网格双靴 LOD0 为 66,716 个位置顶点、130,873 个三角形，分 116 个可编辑部件；运行时合入一个蒙皮资产，不创建逐甲片组件或逐铆钉骨骼。
- 复用 Jason 完整原生骨架和参考姿态。护胫跟随小腿，脚部沿踝／前掌分配权重，踝片与内衬使用过渡权重。未新增动作、Tick、碰撞求解或布料模拟。

## 表面与来源

四槽为锻钢、深色皮革、层压皮底、蜡线。钢面复用已保存的 `ChainmailPants20261004/ArmorRefineV2` 锻钢材质与高度场，保持成套色泽；皮革和皮底由新的周期高度场生成 1024² BaseColor／Normal／ORM。

UV 以 25 cm 标定，材质重复四次得到 6.25 cm 周期。法线为 OpenGL 约定，UE 导入翻绿；ORM 为 R 遮蔽、G 粗糙度、B 金属度。保留 mip 与纹理流送，不增加 POM。高模表面场独立放在 Blender 的 `BAKE_ONLY_SurfaceFields`，不导入游戏。

参考图为本对话 AI 概念图；新几何、皮革高度场和作者脚本为本轮制作。尺度和绑定参考当前 Jason 身体与已导入皮靴，原始角色及 Fab 素材的许可边界仍沿原项目记录，不新增公开再分发声明。

## 配套与接入

靴筒在膝下收口；单独派生皮肤遮挡基础网格，仅分拆靴内的下肢部分，保留原材质区段编号。所有原配方的 Jason 遮挡集合按分拆来源扩展，避免原裤装或旧鞋靴漏遮。仅切换活动 Jason profile，保留旧基础资产。

牛仔裤、工装裤、灰钢锁子甲裤各有独立 `shoe_fit_meshes.ue_armored_boots.Jason` 版本，下段收进靴筒，38–43 cm 高度过渡；换回其他鞋恢复各自原裤装。锁子甲裤只调整裤腿与包边，保留 V2 护膝、护腰形体、材质与权重。

物品初始配置：普通品质、2×3 格、基础防御 24、价格 85，无新增移动或攻击速度惩罚；数值是初始制作配置，未进行平衡测试。物品沿通用装备、掉落、仓库和存档机制接入，不修改玩家库存或存档。

正式图标使用实际已保存模型与四槽生产材质，单只靴斜视、透明背景；同一物品图标供装备栏、背包和仓库使用。掉落网格为一双靴，保留三档 LOD。

## 文件与执行入口

- `SourceAssets/ArmoredBoots20261004/ArmoredBoots.blend`：分件、原生绑定和打包贴图的完整可编辑母版。
- `Jason_ArmoredBoots.json`：游戏几何、面角法线、UV、完整骨架、权重、材质区段。
- `base_fitted.json`、`jeans_fitted.json`、`cargo_fitted.json`、`Jason_ChainmailPants_ArmoredBootsFit.json`：实际来源与配套几何。
- `Tools/ArmoredBoots/extract_inputs.py`：从活动配置读取制作输入。
- `bake_surfaces.py`、`author_geometry.py`、`prepare_companions.py`：材质、建模和配套作者入口。
- `save_assets.py`、`publish_catalog.py`、`finish_background.ps1`：互斥批次内后台保存独立新包、定向更新配置及正式图标生产。
- 目标 UE 根：`/Game/Characters/ModularOutfit20260924/ArmoredBoots20261004`。

## 当前制作状态

可编辑源、表面烘焙、两只靴几何、三款裤脚和身体遮挡数据均已制作。UE 已保存铠甲靴、身体基础网格与三款配套裤装共五个骨骼网格，以及掉落／展示静态网格、三档 LOD 和材质贴图。独立装备和裤脚切换配方已发布到 `items.json`／`modular_outfits.json`。

正式图标已生产并保存到 `Content/ColdSteelData/Icons/ue_armored_boots.png`，作者目录保留副本。保存、发布与图标生产分别以 `saved_assets.json`、`published.json` 和 `icon-production.log` 为回执；后台批次完成标记为 `ARMORED_BOOTS_BACKGROUND_COMPLETE`。

首次材质创建因 Python 属性访问形式中止，修正为 `set_editor_property` 后续接完成；首次日志保留为 `save-assets-material-api-attempt.log`。锁子甲裤沿用的 V2 构件在 LOD 简化中仍有少量多面共享边提示，未将制作成功解释为拓扑、动作或游戏效果验收通过。

未启动 UE 编辑器、游戏、PIE 或额外验收渲染，未测试动作穿插或性能，由用户自行测试。制作三档 LOD 不等于获得了帧率收益。
