# 地牢散件第一批（7 件）来源与许可

全部来自 Sketchfab，**统一为 CC BY 4.0（可商用，必须署名）**。
获取日期 2026-09-22；API 直连、S3 下载走系统代理 `127.0.0.1:7897`（见下）。

## 逐件来源

| key | 作品 | 作者 | 页面 | 许可 | 面数 |
| --- | --- | --- | --- | --- | --- |
| lantern | Rusty Old Oil Lantern | chrisg4919 | <https://sketchfab.com/3d-models/rusty-old-oil-lantern-de28cba29f58414c914298f648da90bf> | CC BY 4.0 | 7,566 |
| cobwebs | Cobwebs Asset Pack | Em Marshall | <https://sketchfab.com/3d-models/cobwebs-asset-pack-2dd4798676d84bc7af5d2a8f5834563a> | CC BY 4.0 | 419 |
| ladder | Wooden Step Ladder Scan LOWPOLY | EFX | <https://sketchfab.com/3d-models/wooden-step-ladder-scan-lowpoly-296b91ddfe7a446db98c9a0f8f5923bd> | CC BY 4.0 | 824 |
| rope | Coiled Rope 2 | TepidGames | <https://sketchfab.com/3d-models/coiled-rope-2-e6fe8fedd3d04b1dac3e32e0dd515cbb> | CC BY 4.0 | 19,988 |
| extinguisher | Fire Extinguisher Old Rusty 3D Scan | grafi | <https://sketchfab.com/3d-models/fire-extinguisher-old-rusty-3d-scan-70a4fdec06c64372ba3a96ae49257ce1> | CC BY 4.0 | 29,984 |
| bucket | Old Rusted Bucket v3 | Coozy | <https://sketchfab.com/3d-models/old-rusted-bucket-v3-ca0755cc9e2d4dfd920e51b6ca9e1243> | CC BY 4.0 | 2,936 |
| barrel | Rusty and Oil Stained Oil Barrel | Sunbox Games | <https://sketchfab.com/3d-models/rusty-and-oil-stained-oil-barrel-c879b42696634752892c7f5e747c4ae4> | CC BY 4.0 | 812 |

许可全文：<https://creativecommons.org/licenses/by/4.0/>

署名文字（随项目对外分发时保留，另见 `FPSGAME/ThirdPartyNotices/DUNGEON_ART_PASS.md`）：

> "Rusty Old Oil Lantern" by chrisg4919 · "Cobwebs Asset Pack" by Em Marshall ·
> "Wooden Step Ladder Scan LOWPOLY" by EFX · "Coiled Rope 2" by TepidGames ·
> "Fire Extinguisher Old Rusty 3D Scan" by grafi · "Old Rusted Bucket v3" by Coozy ·
> "Rusty and Oil Stained Oil Barrel" by Sunbox Games — all licensed under CC BY 4.0.
> Source: Sketchfab (pages above).

## 下载原件（本机保留，不入 Git）

`Receipts/download.json` 记录 14 个包（source + glb）的大小与 SHA-256，共 206.1 MB。原始 zip/glb 在 `D:\FPS3D\_sketchfab_goddess\artpass\download\<key>\`。

| key | source 包大小 | 源内网格 | 源内贴图 |
| --- | --- | --- | --- |
| lantern | 48.3 MB | `source/Lantern01.fbx` | BaseColor / Normal / Roughness / Metallic / AO / Opacity（PNG） |
| cobwebs | 2.3 MB | `source/Test 1.obj`（无 mtl） | Colour 1–3 (jpg) + Alpha 1–3 (jpeg) |
| ladder | 52.5 MB | `source/Stool/Stool.fbx`（名为 Stool） | Diffuse + AO（PNG） |
| rope | 2.1 MB | `source/Rope2.blend` | **无贴图**（纯色材质） |
| extinguisher | 13.7 MB | `source/hasiaci-low/hasiaci-low.obj`（无 mtl） | diffuse / normal / specular / ao（jpg，spec-gloss） |
| bucket | 8.4 MB | `source/Bucket_low.fbx` | **四套**材质贴图（Base / interior / wood / metal） |
| barrel | 61.1 MB | `source/Oil_Barrel.fbx` | AlbedoTransparency / Normal / Roughness / MetallicSmoothness / AO |

## 加工产物（本机）

| 文件 | 大小 | SHA-256（前 16 位） |
| --- | --- | --- |
| `Authored/SM_Prop_Lantern.fbx` | 0.57 MB | `2E88F8738EBF1613` |
| `Authored/SM_Prop_Cobweb_1/2/3.fbx` | 0.03 / 0.02 / 0.02 MB | `A49705763D914A6F` / `0CB8FB648E8C33A5` / `7C188ADD03F5B17B` |
| `Authored/SM_Prop_StepLadder.fbx` | 0.04 MB | `1CE814A774BE2CDC` |
| `Authored/SM_Prop_Rope.fbx` | 0.41 MB | `69AB40E4C8C01253` |
| `Authored/SM_Prop_Extinguisher.fbx` | 2.40 MB | `3B017C85B1526D84` |
| `Authored/SM_Prop_Bucket.fbx` | 0.18 MB | `756C28DA3E7568D1` |
| `Authored/SM_Prop_OilBarrel.fbx` | 0.05 MB | `6CF5B6991333F78B` |

贴图统一由 8192/4096 级别降到 **2048**（小物件足够），共 37 张，见 `Receipts/textures.json`。可编辑源 `.blend` 与贴图路径同样留本机。

## 修改说明（CC BY 要求记录改动）

1. **几何**：只做归一化——等比缩放到真实尺寸（灯笼 0.32 m、阶梯 1.10 m、绳索盘 0.45 m、灭火器 0.55 m、水桶 0.30 m、油桶 0.88 m 高），底面中心为 pivot、底面 Z=0；蛛网按材质拆成 3 张独立卡片并各自归零，尺寸保持源比例（×0.01 cm→m）。
2. **贴图**：降采样到 2048，未改内容；未接入的图见下。
3. **UE 材质**：源材质结构各异，统一重建为项目规范——BaseColor（可乘 AO 与 Tint）、Normal（翻转绿通道）、Roughness、Metallic 参数化，实例承载数值。**蛛网与油桶用 MASKED**（蛛网用独立 alpha 图，油桶用 albedo 自带 alpha）。
4. **未接入的源图**：灯笼的 Opacity（会打成镂空，玻璃另做半透明材质）、灭火器的 specular（spec-gloss 流程，粗糙度改用常数 0.7）。
5. 关闭 Nanite；碰撞按件：实体件用三角面碰撞，蛛网卡片 `none`。

网格拓扑、UV 与贴图内容未修改，未重新烘焙。
