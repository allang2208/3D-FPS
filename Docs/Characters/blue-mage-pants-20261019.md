# 黑色法师长裤 · 修身西裤 V2

用户已批准 `SourceAssets/BlueMagePants20261019/Design/black-mage-pants-concept-v02.png`，继续模型制作与接入。V1 紧身版仅保留作设计历史，不作为模型来源。

## 造型与制作

- 哑黑精纺织物，腰部贴合，臀部、大腿与小腿保留穿着余量；浅前褶、纵向裤线、斜插袋与后嵌线袋。
- 细蓝侧边、少量银色星藤纹、低矮星形腰扣与蓝色宝石；裤脚平直，无弹性束口。
- 基于当前 Jason 原生骨架及已有腰部截面制作，腰胯与双腿连接先焊接，再按原生身体三角面转移权重；最多 8 个骨骼影响。
- 可编辑源：`SourceAssets/BlueMagePants20261019/Exports/BlueMagePants_Editable.blend`，包含绑定后的模型与独立 `BAKE_ONLY_SurfaceFields` 高细节表面源。
- 三套 2048 材质图：Worsted / Cobalt / Facing；每套保留 BaseColor、Normal、ORM、16 位 Height 与原始物理高度字段。4 cm 织物周期，由解析高度场生成法线，不使用视差遮蔽。
- 标准完整模型 63,012 三角形（包括原生腰部补片），法袍内搭版本 26,172 三角形。UE 生产保存阶段生成三档 LOD：1 / 0.65 / 0.4。

## 装备与组合

物品 ID：`ue_blue_mage_pants`。背包占格 2×3，装备槽 15（pants）。沿用普通裤装的属性框架，无额外套装效果。

| 穿着组合 | 完整裤装源 | 法袍内搭源 |
| --- | --- | --- |
| 普通鞋 / 无靴 | Jason_BlueMagePants | Jason_BlueMagePants_RobeInner |
| 短靴 ue_boots | Jason_BlueMagePants_ShortBootsFit | Jason_BlueMagePants_ShortBootsFit_RobeInner |
| 皮靴 / 铠甲靴 | Jason_BlueMagePants_HighBootsFit | Jason_BlueMagePants_HighBootsFit_RobeInner |
| ST6 战术靴 | Jason_BlueMagePants_ST6BootsFit | Jason_BlueMagePants_ST6BootsFit_RobeInner |

靴子版本只调整下段裤腿，腰胯和大腿保持 V2 西裤版型。法袍内搭从膝关节上方 2 cm 截取，保留完整小腿、裤脚和鞋子；在已有法袍 `underlayer_meshes` 中新增四条映射。法袍当前 MovementFit20261019 资产、物理参数及原有其他内搭映射不变。

第一人称低头可见身体与第三人称身体使用当前 Jason 共用身体装备路径。裤装由 `FPSModularOutfitComponent` 根据鞋子选择，再应用法袍内搭替换；弓、枪、法杖和双手近战等武器继续通过共用路径使用该裤装。

## 图标与落地模型

标准图标由实际裤装模型生成，透明 PNG 为 213×320，正交视角，约 91% 填充；同时保存相同视角的静态展示网格和 UE UI 纹理。落地拾取网格使用纯衣物表面，不含原生皮肤补片。

背包需要的两个 PNG 路径同时提供：

- `Content/ColdSteelData/Icons/ue_blue_mage_pants.png`
- `Content/ColdSteelData/Icons/BlueMagePants20261019/ue_blue_mage_pants.png`

## 生产入口与完成边界

按顺序使用 `Tools/BlueMagePants` 下的 `bake_surfaces.py`、`author_geometry.py`、`prepare_runtime.py`、`save_editable.py`、`run_asset.ps1`、`publish.py`。Blender 脚本使用后台运行；UE 沿用共用批次互斥，优先已有编辑器桥，否则后台 commandlet。

源码与导出完成记录：`construction_receipt.json`、`surface_receipt.json`、`runtime_preparation.json`、`editable_receipt.json`。实际 UE 保存以 `saved_assets.json` 为准，装备表发布以 `published.json` 为准，均在该 SourceAssets 家族目录中。

本次不主动进行游戏、动作、截图或运行时验收，交由用户试玩。


2026-10-19 用户要求的衣物与联机复核、已修复项和实测边界见 [法师套装复核](blue-mage-set-audit-20261019.md)。
