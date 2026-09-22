# SVD（德拉贡诺夫狙击步枪）来源与许可

| 项 | 内容 |
| --- | --- |
| 作品 | **SVD (Dragunov sniper rifle)** |
| 作者 | **LeroyCake**（<https://sketchfab.com/leroycake>） |
| 页面 | <https://sketchfab.com/3d-models/svd-dragunov-sniper-rifle-2ac78fb5a0eb40f5a02a5b0a9f566abf> |
| 许可 | **CC BY 4.0**（`CC-BY-4.0`，写在 glb 的 `asset.extras.license`）；允许商用，**必须署名** |
| 作者自述 | "Another weapon made by myself. A simple soviet/russian sniper rifle - SVD. Caliber 7.62. Plastic stock version" |
| 获取日期 | 2026-09-22（Sketchfab Data API v3，用户提供的 token） |
| 规模 | 31,516 面 / 16,669 顶点（glb 实测 31,489 面）、10 张 4096² 贴图、无骨骼、无动画 |

署名文字（随项目对外分发时保留，另见 `FPSGAME/ThirdPartyNotices/SVD_DRAGUNOV.md`）：

> "SVD (Dragunov sniper rifle)" by LeroyCake, licensed under CC BY 4.0.
> Source: https://sketchfab.com/3d-models/svd-dragunov-sniper-rifle-2ac78fb5a0eb40f5a02a5b0a9f566abf

## 下载原件（本机保留，不入 Git）

| 文件 | 大小 | SHA-256 |
| --- | --- | --- |
| `source_svd-dragunov-sniper-rifle.zip` | 37.9 MB | `6E41378006E73A7E1153FB05F2DB504C6182BBEAEAADFF6B5D44C3468415F516` |
| `svd_source.glb`（Sketchfab 转换包，本轮实际使用的几何来源） | 6.1 MB | `D761E751FE97C606797DF31681F1ADD513E31C48022E6075527DD41FB6242240` |

## 为什么用 glb 而不是作者的 model.dae

原包内网格是 **Collada**（`source/model/model/model.dae`），而**本机 Blender 5.1 已不再附带 Collada 导入插件**（`io_scene_collada` 不可用，算子集里没有 `collada_import`）。Sketchfab 转换出的 glb 与原网格一致（25,440 + 6,049 = 31,489 面，两个材质槽，与页面申报的 31,516 面相符），因此几何取自 glb；**贴图仍用原包里的 10 张 4096² 原图**（glb 内嵌的贴图是压缩过的）。

## 源结构

| 部件 | 源对象 | 材质槽 | 面数 | 对应贴图组 |
| --- | --- | --- | --- | --- |
| 枪体 | `defaultMaterial` | `material_1` | 25,440 | `svd_*`（albedo / normal / roughness / metallic / AO） |
| PSO-1 瞄准镜 | `defaultMaterial.001` | `material` | 6,049 | `pso_*`（同上五张） |

源的**法线是全平滑**：`has_custom_normals=True`，0 个大于 25° 的锐边对，最大夹角 0.05°——硬边与细节由 4096 法线贴图承担。这是作者的处理方式，导入与导出都未改动。

## 加工产物（本机）

| 文件 | 大小 | SHA-256 | 说明 |
| --- | --- | --- | --- |
| `Authored/SM_SVD_Body.fbx` | 1.23 MB | `B90D7FD4197984AC1F3930DAECA9BB8EA5B6022E934F52831339BA7D05EB7C17` | 枪体：机匣、枪管、护木、枪托、握把、准星、机匣顶盖，19,252 面 |
| `Authored/SM_SVD_Magazine.fbx` | 0.32 MB | `1EE58527E64049216EDBC3ECF5CE0320B4DA3E9D6AD54BBE7E1CB791F5C13FC0` | 弹匣（53 壳 / 4,936 面） |
| `Authored/SM_SVD_Trigger.fbx` | 0.04 MB | `9644E0330F6C1CB0015D6EFE0A8AA331DA5C6E762829756605EE797F5BFC7706` | 扳机（17 壳 / 428 面） |
| `Authored/SM_SVD_ChargingHandle.fbx` | 0.02 MB | `4DF29935E75F901194B33C37F9B39D2C6F0831A1B297993F504C8F940E31FFBE` | 拉机柄（5 壳 / 96 面） |
| `Authored/SM_SVD_SafetyLever.fbx` | 0.06 MB | `8BB64AB41FA44AB4230739A4093A59DD673F1F25052C860694A4479EE6C77702` | 保险／快慢机（20 壳 / 728 面） |
| `Authored/SM_SVD_ScopeBody.fbx` | 0.25 MB | `3955417528C84AF256560A05CC50C40DC9FA512E98F15B6D3EEC3D8257E98E07` | PSO-1 镜筒（3,859 面） |
| `Authored/SM_SVD_ScopeMount.fbx` | 0.13 MB | `87342BB3776BD3F8BBC3D86F41F0C7BECBF4AA2B73E6B848E36B9D7CE5185B72` | PSO-1 侧装镜座卡箍（97 壳 / 1,835 面） |
| `Authored/SM_SVD_ScopeLens.fbx` | 0.04 MB | `36CA71D646163E9765EB47DB3CA2C13FD48F79B8A0C0357EDDD08F1B1590D4BE` | PSO-1 镜片组（11 片 / 355 面） |
| `Authored/SK_SVD_Manny.fbx` | 3.25 MB | `AE8474E4417EE8C4A65B8AFCF7FDA95CF05153664BAC1A4E8400BD0F52C21A66` | 视图模型：共享 Manny 手臂 + 上述八件，刚性绑到 WPN_* 骨骼 |
| `Authored/SVD_Mechanical.blend` | 5.71 MB | `C78C2E3A7056F056DFEA14FB9F59A507D38CBB2E28ABF68BC6AD84D856EB8087` | 分件场景（可编辑源） |
| `Authored/SK_SVD_Viewmodel.blend` | 62.07 MB | `A09966599460BACFF0B8D858B158E5E9E0604343C3846668E82123F8DF862788` | 装配场景：对齐 + 手臂 + 绑定 |
| `Textures/`（10 张 4096²，法线为无损 PNG） | 37.3 MB | 见 `Receipts/textures.json` | 源贴图，未重压 |

## 修改说明（CC BY 要求记录改动）

1. **几何**：只做归一化——等比缩放到实枪全长 **1.225 m**（源长 1.7208 单位，比例 0.711862），上方 +Z；所有部件共用整枪包围盒中心作为原点，**未逐件归零**，保留装配关系。实测（`Receipts/weapon_space.json`、`Receipts/roll_vs_m4.json`）导出场景中**枪口在 +Y**（该端截面仅 6.5 cm 高，枪托端 14.4 cm），并随 `axis_forward='-Y'` 导出；**M4 自己的 FBX 走同一条映射**（包围盒中心 Blender +23.4 cm → UE −23.44 cm），因此两者的朝向约定一致，本件不需要额外的 90°/180° 修正。
2. **机械分件**：源枪体由 758 个独立壳体组成、机械件与枪体混在一起。按测量区域**重组既有壳体**（不裁切任何表面）分出弹匣（53 壳 / 4,936 面）、扳机（17 壳 / 428 面）、拉机柄（5 壳 / 96 面）、保险杆（20 壳 / 728 面）；面数总和 31,489 与源一致。判定区域与证据见 `README.md` 与 `Receipts/shells_below.json`。
3. **贴图**：4096² 保持原尺寸；albedo / roughness / metallic / AO 为原 JPEG 复制（未重压），normal 转无损 PNG。
4. **UE 材质**：源材质结构在 UE 内重建为项目规范——BaseColor（× AO × Tint 参数）、Normal（4096、翻转绿通道）、Roughness（× RoughnessScale）、Metallic，数值由材质实例承载；不透明、单面。
5. 关闭 Nanite；碰撞用三角面（`CTF_USE_COMPLEX_AS_SIMPLE`）。

网格拓扑、UV 与贴图内容未修改，未重新烘焙；分件只是壳体归属的重新划分。
