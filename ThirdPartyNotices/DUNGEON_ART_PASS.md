# 地牢散件第一批（7 件）第三方素材声明

七件全部为 **CC BY 4.0**，允许商用，**必须署名**。随项目对外分发时保留本声明。

许可：<https://creativecommons.org/licenses/by/4.0/>

| 作品 | 作者 | 来源 |
| --- | --- | --- |
| Rusty Old Oil Lantern | chrisg4919 | <https://sketchfab.com/3d-models/rusty-old-oil-lantern-de28cba29f58414c914298f648da90bf> |
| Cobwebs Asset Pack | Em Marshall | <https://sketchfab.com/3d-models/cobwebs-asset-pack-2dd4798676d84bc7af5d2a8f5834563a> |
| Wooden Step Ladder Scan LOWPOLY | EFX | <https://sketchfab.com/3d-models/wooden-step-ladder-scan-lowpoly-296b91ddfe7a446db98c9a0f8f5923bd> |
| Coiled Rope 2 | TepidGames | <https://sketchfab.com/3d-models/coiled-rope-2-e6fe8fedd3d04b1dac3e32e0dd515cbb> |
| Fire Extinguisher Old Rusty 3D Scan | grafi | <https://sketchfab.com/3d-models/fire-extinguisher-old-rusty-3d-scan-70a4fdec06c64372ba3a96ae49257ce1> |
| Old Rusted Bucket v3 | Coozy | <https://sketchfab.com/3d-models/old-rusted-bucket-v3-ca0755cc9e2d4dfd920e51b6ca9e1243> |
| Rusty and Oil Stained Oil Barrel | Sunbox Games | <https://sketchfab.com/3d-models/rusty-and-oil-stained-oil-barrel-c879b42696634752892c7f5e747c4ae4> |

要求的署名文字：

> "Rusty Old Oil Lantern" by chrisg4919, "Cobwebs Asset Pack" by Em Marshall,
> "Wooden Step Ladder Scan LOWPOLY" by EFX, "Coiled Rope 2" by TepidGames,
> "Fire Extinguisher Old Rusty 3D Scan" by grafi, "Old Rusted Bucket v3" by Coozy and
> "Rusty and Oil Stained Oil Barrel" by Sunbox Games — licensed under CC BY 4.0.
> Sources: Sketchfab (links above).

## 用途与状态

导入位置：`/Game/Dungeons/ArtPass20260922/{Meshes,Materials,Textures}`。
2026-09-22 导入时尚未在关卡内摆放。后续地牢随机摆放由 `AuthoredDungeonDressing` 接入；本次源码发布保留署名，模型与贴图二进制仍按 `Docs/AssetSetup.md` 从合法本机素材恢复。

## 修改说明

等比缩放到真实尺寸并统一 pivot（底面中心）、贴图降采样到 2048、在 UE 内重建材质（BaseColor/Normal/Roughness/Metallic 参数化，蛛网与油桶用 MASKED + 独立 alpha／albedo alpha，蛛网双面）、关闭 Nanite、碰撞用三角面（蛛网无碰撞）。未修改网格拓扑、UV 或贴图内容，未重新烘焙。逐件细节与散列见 `SourceAssets/DungeonArtPass20260922/PROVENANCE.md`。
