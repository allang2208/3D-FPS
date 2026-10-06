# MetaHuman Boots 鞋靴装备接入

物品 ID 为 `ue_boots`，显示名“系带皮靴”，使用现有鞋靴槽 13 和 2×2 背包占格；沿用现有装备、替换、卸下、仓储、丢弃、拾取和存档流程。装备栏仍位于裤子正下方。

制作源为用户本地的 `VaultCache/FabLibrary/MetaHuman_Boots-c6596c37/metahuman/UE_5.7/oa_boots.mhpkg`。来源、文件散列及包内清单保存在 `SourceAssets/BootsEquipment20261004/provenance.json`，仅作本地项目接入。本次保留原生材质、贴图和靴子结构，从 `CA_Boots_m_med_nrw` 导出实际服装网格，再适配 Jason；包内 `CombinedSkelMesh` 是体型参考，不能当作靴子。

派生资产位于 `/Game/Characters/ModularOutfit20260924/BootsEquipment20261004`：

- `SK_Jason_Boots`：Jason 骨架与蒙皮，三档 LOD。
- `SK_Jason_Base`：在当前身体覆盖网格上细分靴筒遮挡区域，保留原生身体形状、材质和已有区域编号。
- `SK_Jason_Jeans_BootsFit`、`SK_Jason_Cargo_BootsFit`：只在穿 `ue_boots` 时选用的裤脚搭配版本。
- `Pickups/SM_Boots`：双靴掉落实体，模型居中，由现有拾取物理根提供碰撞与重力。
- `Icons/SM_Boots_Display`：单只斜视的独立图标显示网格，使用原生材质；正式透明 PNG 写入 `Content/ColdSteelData/Icons/ue_boots.png`。

`FPSModularOutfitComponent` 在已有鞋子参与的外观键发生变化时，读取裤子配置 `shoe_fit_meshes[鞋子物品 ID][rig_profile]`；无适配版本时使用原 `rig_meshes`。新网格继续进入现有异步加载批次，不增加 Tick、同步运行时加载或新装备槽。身体覆盖区域扩展同步到已有 Jason 衣物配置，换回休闲鞋、赤脚时保留原裤子外观。

制作脚本位于 `Tools/BootsEquipment`。顺序为恢复本地包、用 `Tools/LowerBodyEquipment/AuthoringHost` 的 `BakeOutfit` 单资产参数导出供体、`extract_inputs.py` 读取原生输入、`fit_boots.py` 适配、`save_assets.py` 保存资产、`publish_catalog.py` 注册目录，最后用 `ColdSteelWeaponIconCatalog -Definition=ue_boots` 生成正式图标。重新发布已有定义时需明确更新该条目，不重复插入。

执行约定：后台制作、必要构建与保存；不启动编辑器或游戏，不运行测试或验收。资产保存、源码构建与游戏内表现分别报告。

完成记录：上述六个正式派生资产、物品目录／换装配置和 `ue_boots.png` 均已落盘；原始双靴 LOD0 为 10,614 顶点、17,932 三角面。`FPSGAMEEditor Win64 Development` 构建成功，包含 `FPSModularOutfitComponent.cpp` 的编译，结果摘录在 `SourceAssets/BootsEquipment20261004/build-completion.txt`。资产保存与图标制作日志分别为同目录 `save-assets-new-only.log`、`icon-ue_boots.log`。未运行游戏测试，搭配和动态穿戴表现由用户测试。
