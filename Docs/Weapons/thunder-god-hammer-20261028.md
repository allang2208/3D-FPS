# 雷神之锤接入记录

武器 `ue_thunder_god_hammer` 使用用户提供的 `Meshy_AI_Stormbreaker_Runehamm_1028015020_texture.glb`。制作源、可编辑 Blender 文件、导出模型与执行回执保存在 `SourceAssets/ThunderGodHammer20261028/`。

## 外观与握持

整锤总长 115 cm，宽约 34.14 cm、厚约 11.81 cm；以现有双手锤的 WPN_root、双手握区和颈部接口适配长柄。保留输入模型的锤首、中央三角交结纹、UV 和原生 PBR，未减面。原始输入为 392,646 三角形；拆分模块补口后数量增加。

基础模型与材质位于 `/Game/Weapons/ThunderGodHammer20261028`，模块位于其 `ModulesV1` 子目录。整模及原装模块使用 Nanite 与完整回退几何；用于通用符文覆盖的长柄保留常规渲染路径。通用改造件复用对应现有材质。

## 模块与枪匠

六个原装模块为 `head_mount`、`hammer_heads`、`neck`、`shaft`、`grip`、`pommel`；现有五栏枪匠菜单展示锤头、中座、符文、握柄、尾锤。

- 4 件通用锤头、5 件通用中座、3 件通用握柄、4 件通用尾部选项已按本锤实际接口重制连接区。
- 中座包括破势古印座和鸣雷疾驱座；它们沿用已安装配件对应的现有能力。
- 5 种通用符文共享现有资源，长柄覆盖材质使用本锤局部坐标。
- 其他武器的专属锤头、尾锤和固有被动未加入本武器配件表。

运行数据为 `Content/ColdSteelData/thunder-god-hammer-modules.json` 和 `thunder-god-hammer-gunsmith.json`。枪匠原装／类别缩略图使用真实部件制作，沿用金属边框灰色图标规范；附加符文图标共享既有图案。背包图标由 `ColdSteelWeaponIconCatalog -Definition=ue_thunder_god_hammer` 按实际装配和原生 PBR 生成。

## 战斗、动作与发放

物品登记在 `items.json`，数值公式独立登记在 `combat-weapon-formulas.json`，初值沿用当前钢制战锤的力量／体质公式。通过 `tool_kind=warhammer` 使用当前轻击、蓄力、重击、连击、格挡、检视、移动及第三人称映射；未复制动画资产或覆盖 `player_body.json`。共享依赖清单见制作源中的 `animation_manifest.json`。

现有 `GrantStartingArmory` 流程按本物品 ID 幂等发放到军械库，适用于新旧存档。原始 GLB 无发光贴图，本次保留蓝色原生刻纹，不新增雷神之锤的固有雷击技能。

源码入口涉及 `WarhammerGunsmith.cpp`、`FrostSwordRunes.h`、`AncientSealSeat.h`、`GunsmithModificationTier.h` 和 `ColdSteelWarehouseModel.cpp`；打包目录登记在 `Config/DefaultGame.ini`。

## 交付边界

仅完成制作、资产保存、数据接入及必要构建。后台图标生成属于生产资产步骤；未启动编辑器界面或游戏，未进行自测、运行回归或验收，交由用户测试。每阶段实际结果以制作目录的 `delivery.json` 及各阶段回执为准。

## 用户要求复查后的更新

用户随后要求“自己检查一遍”。已执行目录、保存资产、几何及隔离原生调用检查；修正鸣雷疾驱座模型识别漏接，以及通用附加符文的长柄材质识别／覆盖材质复用漏接。完整结果、首次失败和最终构建回执见 `SourceAssets/ThunderGodHammer20261028/Review20261028/review.md` 与 `summary.json`。本轮未进行真实 UDP 双端或连续动作画面验收。
