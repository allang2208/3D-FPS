# 女神石像套件（noe-3d.at）第三方素材声明

本声明用于 CC BY 4.0 的署名要求，随项目对外分发时保留。

## 需要署名的三件（CC BY 4.0）

- **Flora** — 作者 noe-3d.at — <https://sketchfab.com/3d-models/flora-5cae3fbe60ba4a79b83ed12e0c26db44>
- **Muse** — 作者 noe-3d.at — <https://sketchfab.com/3d-models/muse-209c7842f0ab416cbdbd8a7484ab8930>
- **Barockstatue** — 作者 noe-3d.at — <https://sketchfab.com/3d-models/barockstatue-ebc9a140626842fd8804b38c1dc8b8c9>

许可：**CC BY 4.0** — <https://creativecommons.org/licenses/by/4.0/>（允许商用，必须署名）

要求的署名文字：

> "Flora", "Muse" and "Barockstatue" by noe-3d.at, licensed under CC BY 4.0.
> Source: https://sketchfab.com/www.noe-3d.at

## 无需署名但一并记录的两件（CC0 1.0）

- **Venus** — <https://sketchfab.com/3d-models/venus-47c7f4d3b6e640858e1d3afac28c1766> — CC0 1.0
- **Magna-Mater-Brunnen** — <https://sketchfab.com/3d-models/magna-mater-brunnen-f6fa0a62a03149319e4fee21cb6dd5af> — CC0 1.0

## 用途

地牢场景中的古代雕像资产池：`/Game/Dungeons/StatueSet20260922`。截至本声明日期**尚未在关卡内摆放**（仅导入资产）。同作者的另一件 Diana 单独记录在 [GODDESS_STATUE.md](GODDESS_STATUE.md)。

## 修改说明

五件均做了同等加工：立正并统一朝向到正面 +X、等比缩放到 2.0 m（大母神坐像 1.8 m）、底面中心为 pivot 且底面 Z=0、漫反射图集 8192² → 4096²、UE 内新建材质与材质实例（原 glTF 只有 baseColor）、关闭 Nanite、碰撞改用三角面。网格拓扑、UV、法线与贴图内容未修改，未重新烘焙。逐件前后尺寸与散列见 `SourceAssets/DungeonStatueSet20260922/PROVENANCE.md`。
