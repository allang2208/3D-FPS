# 蟠螭展岳：镇岳专属特殊护手

用户于2026-10-06认可效果图并要求建模接入。候选依据 `../PanChiGuardConcept20261006/panchi_zhanyue_guard_concept_v1.png`；本轮制作真实模型，不更换原厂默认项。

## 模型与材质

原厂中心取自 `../BladeV3/XuanChi_BladeV3_Editable.blend` 中 `SM_XuanChi_Guard_V3`：保留中央青玉、刀根接座和握柄接口，保留中心面角 UV 与自定义法线；只截取需替换的两侧旧翼。新翼按认可的蟠螭云卷形态制作约40cm总跨度，左右镜像，双面实体浮雕最高3.2mm，曲面承力主体沿长度变薄，翼根加厚肩部衔接中央轮廓。云孔贯通，侧壁封闭，末端上扬圆卷。

作者路线为内置 image_gen 生成专用灰度雕纹源，再由 Python 烘焙高度/法线/铜色 PBR、Blender 制作实体翼体及装配；不是Meshy模型。灰度图只提供纹饰域，承力厚度、对称、装配坐标、翼根过渡和原厂安装口由作者脚本决定。背面纹饰为镜像设计补全。素材提示词保留在 `artwork_provenance.json`。

`PanChi_Guard_Editable.blend` 是可编辑母版；`Export/` 有厘米 FBX 与带材质 GLB。三档 LOD 为272682、149975、68170三角形。近景密度用于原厂高精度中心与双面龙云浮雕；不表示实测性能。3个材质区，新增一套2048×1024铜色BaseColor/ORM/Normal；主浮雕由几何承担，鳞纹刀痕由切线法线补充。原厂中心继续绑定现有亮铜/青玉材质和埋入式刀根钢材质，旧白膜图未复活。

## 接入

路径：玄螭镇岳 → 护手 → 特殊改造 → 蟠螭展岳。`panchi_zhanyue` 仅在 `ue_xuanchi_zhenyue` 可选。金色特殊分类由 `GunsmithModificationTier.h` 登记，排序沿通用→特殊→传说。未指定数值效果，`stats` 留空，只改变外观。

模块路径 `/Game/Weapons/XuanChiZhenYue20261004/PanChiGuard20261006`，继续使用 `xuanchi_hilt_v1`、原有WPN_root装配与 `gunsmith_parts.guard` 存档合同。新增材质同步建立旋风时序响应派生；保留剑身符文、握点修正、长柄偏移和剑穗物理。

图标从最终实际模型制作灰阶素材，再沿现有厚金属方框、四角铆钉和内圆环规范合成。只登记单个共享键 `guard_panchi_zhanyue`，不生成另一份武器前缀副本。图标制作是接入所需生产素材，不是额外验收渲染。

## 重建入口与交付状态

1. `surface_recipe.py` 烘焙纹饰、几何参数和PBR。
2. Blender后台执行 `author_guard.py`，导出模型与三级LOD。
3. Blender后台执行 `render_icon_subject.py` 制作图标主体；图标成图与提示词保留 `Icons/`。
4. `build_and_import.ps1 -BuildOnly` 完成特殊分类原生Editor/Game构建。
5. `build_and_import.ps1 -SkipBuild` 运行资产保存与目录发布。

资产实际保存以 `import_receipt.json` 为准，目录发布见 `catalog_receipt.json`；只在实际保存后登记改造项。源模型、导出和图标不替代UE保存回执。未主动打开编辑器、运行游戏、检查玩法或制作验收画面；由用户自行测试。未修改存档或替用户装备。

2026-10-06本轮完成：Editor/Game构建均为Succeeded，无界面导入退出码0并保存7份资产，目录发布回执complete=true。完整交付记录 `delivery.json`。

## 后续批准的玩法

现行正式效果为强化上挑升龙：法阵采用本护手的双螭、展翼云纹、山岳形中轴和中央玉饰，位移后前方 3 米生成，直径 4.4 米，与加长金龙持续 1.5 秒。现行制作与接入记录以 `../PanChiUppercut20261007/production.md` 为准；改造面板增加完整触发与效果说明。下面保留最初玩法方案的历史记录。

用户随后批准“ 双螭缚岳 ”方案，护手保留上述模型和特殊分类，追加格挡蓄势、重击破韧与牵引。当前数值和实现记录见 `../PanChiEffects20261006/production.md`；安装器读取该目录 `effects.json`，不再以最初的空属性覆盖已制作玩法。上文空 `stats` 仅记录外观首次交付时的范围。
