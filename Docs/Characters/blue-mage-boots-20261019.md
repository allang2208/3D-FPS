# 蓝黑法师长靴 · V1

用户已批准 `SourceAssets/BlueMageBoots20261019/Design/blue-mage-boots-concept-v01.png`，继续精确模型制作与装备接入。

## 造型与源模型

黑色细纹皮革、深蓝织物嵌片、细银色星藤纹、外侧蓝宝石扣、内侧拉链。正常圆杏形鞋头，低跟鞋底，靴筒止于膝下。脚踝区域保留柔软压褶。

鞋面与靴筒为连续环线网格，蓝色嵌片在同一表面上划分材质。靴口外壁、端面与内壁连续；鞋底有实体边缘、低跟、足弓与浅防滑纹。银纹和接缝沿实际鞋面分布。

原生参考：`SourceAssets/BlueMagePants20261019/native_reference.json`，绑定源为当前 Jason 原生身体。靴筒随 calf，踝部在 calf / foot 之间平滑过渡，前掌与鞋底随 foot / ball 弯曲；所有部件使用同一权重函数，不增加独立动画或逐帧形状修正。

可编辑源：`SourceAssets/BlueMageBoots20261019/Exports/BlueMageBoots_Editable.blend`。
骨骼导出：`SourceAssets/BlueMageBoots20261019/Exports/Jason_BlueMageBoots.fbx`。

当前双靴游戏母版共 106,712 三角形，包含内壁、装饰线、拉链和鞋底；单只展示模型独立。UE 保存生成 1 / 0.65 / 0.4 三档骨骼 LOD，静态展示与拾取也保留三档 LOD。近景双靴保留实体开口、曲面与装饰轮廓，不将表面高模导入运行时。不据此宣称性能测试结果。

## 材质

四套 2048 贴图：Leather、Cobalt、Lining、Rubber。每套保留 BaseColor、Normal、ORM、16 位 Height 和 `HIGH_*.npz` 物理高度源；4 cm 周期与同一高度场的切线法线对应。可编辑文件内另有 `BAKE_ONLY_SurfaceFields` 位移高模，排除在 FBX 导出之外。

七个材质槽：BlackLeather、CobaltWoven、SilverEmbroidery、DarkThread、BlackLining、RubberSole、Sapphire。主体为不透明表面，纹理有 mip 与流送，未增加 POM、透明毛发壳或靴子布料模拟。

## 裤脚、身体与法袍

靴筒以当前高筒靴的原生截面为基准，径向增加 3.5 mm 的容纳量，沿用当前 `ue_armored_boots` 的裤脚适配资源。新鞋键为 `ue_blue_mage_boots`，分别登记到以下七个现有裤装：

| 裤装 | 使用的组合来源 |
| --- | --- |
| 黑色法师长裤 | 当前 HighBootsFit |
| ST6 战术长裤 | 当前 HighBootsFit |
| 烟灰七分裤 | 当前 CapriTailored_HighBootsFit |
| 皮革裤 | 当前 LeatherPants_HighBootsFit |
| 锁子甲裤 | 当前 ChainmailPants_ArmoredBootsFit |
| 牛仔裤 | 当前 Jeans_ArmoredBootsFit |
| 工装裤 | 当前 Cargo_ArmoredBootsFit |

新靴身覆盖当前原生身体材质段 4、11、13、15、16，这些段的最高点为 37.54 cm，靴口约为 38.3–38.9 cm。上方裸露小腿继续由身体绘制，不隐藏整条腿，不另附重复皮肤。

法袍已有的完整小腿内搭与 MovementFit20261019 布料保持原样。新长靴整体低于膝部裁切线，在 `underlayer_meshes` 中明确将靴子路径映射到自身，保留整双靴子及鞋底。所有武器继续使用 Jason 共用身体装备路径；第一人称可见下身与第三人称使用同一装备选择机制。

## 物品与图标

物品 ID `ue_blue_mage_boots`，鞋靴槽 13，背包占格 2×3。沿用普通鞋靴属性框架，无稀有度、额外套装奖励或移动速度改动。

图标由实际生产模型与材质渲染，为单只空靴三分之四视角，213×320 透明 PNG；约 91% 填充，另保存与 PNG 同角度的 UE 静态展示网格和 UI 纹理。拾取模型与穿戴模型保留双靴。

- `Content/ColdSteelData/Icons/ue_blue_mage_boots.png`
- `Content/ColdSteelData/Icons/BlueMageBoots20261019/ue_blue_mage_boots.png`

## 制作入口与交付边界

`Tools/BlueMageBoots/bake_surfaces.py` → Blender 后台 `author_geometry.py` → `save_editable.py` → `run_asset.ps1` → `publish.py`。现有裤装改换生产资源后，运行本家族的 `publish.py` 重新合并当前高筒适配路径；法师裤自己的发布入口也会保留已安装的法师长靴组合。

本家族 `construction_receipt.json`、`surface_receipt.json`、`editable_receipt.json` 记录源与导出。UE 实际保存记录为 `saved_assets.json`，装备表发布记录为 `published.json`。不得只凭脚本存在宣称已导入。

本次不主动进行游戏、动作、截图或运行时验收，由用户试玩。


2026-10-19 用户要求的衣物与联机复核、已修复项和实测边界见 [法师套装复核](blue-mage-set-audit-20261019.md)。
