# 外部资产许可证记录

## _dl_ak47_adamkokrito.glb（当前下载版 AK-47）

- 来源：Poly Pizza https://poly.pizza/m/2zXzvGavqci
- 作者：AdamKokrito
- 许可证：CC-BY 3.0（需署名）
- 署名要求：使用本模型需注明"AK47 by AdamKokrito (Poly Pizza), CC BY 3.0"
- 用途：3-dfps 默认 AK-47 视模（下载版）
- 2026-08-09 下载；已通过 test_ads_calibration 全绿（自动定向/缩放/机瞄校准/弹匣检出）

## akm_sketchfab_prep.obj（当前默认武器，2026-08-09 起）

- 来源：Sketchfab https://sketchfab.com/3d-models/akm-lowpoly-game-ready-b09ba6a7d56246adaff76ad091e4dc72
- 作者：sami uddin（@rameezuddin14）
- 许可证：CC Attribution（CC-BY），需署名
- 原始下载：21.9k tris / 11.3k verts / 4096×4096 PBR 贴图（Textures/PBR 组，
  TGA 转 PNG 2048 存于 assets/models/ak/akm_sketchfab_tex/）
- 预处理（tools/ai-gen/prep_akm_obj.py）：剔除旁置子弹道具、Z→X 转正、矫正 6° 倾斜、
  归一化 1m、保留 UV 并生成 MTL 引用 PBR 贴图
- PBR 补丁（tests/export_pbr_mesh.gd）：Godot OBJ 导入只吃 albedo/normal，
  金属/粗糙/AO 按命名约定补入并导出 akm_sketchfab_pbr.tres（游戏引用此资源）
- 已通过 test_ads_calibration 全绿；GLM 评审：PBR 全通道接入后打磨 6/10、造型 7/10

## 备选

- _dl_akm_jtoastie.glb（已删除）：Poly Pizza https://poly.pizza/m/52kQzphmeF ，J-Toastie，CC0；
  评审造型 4/10，过于抽象，2026-08-09 清理旧资产时一并删除
- 体素方向候选：CGTrader AK74 Voxel Gun（免费，需注册账号下载）
  https://www.cgtrader.com/free-3d-models/military/gun/ak74-voxel-gun

## TACZ AK-47 (test stand-in, since 2026-08-09, NOT a release asset)

- Source: Timeless and Classics Zero 1.1.8-hotfix built-in gunpack tacz_default_gun
  (Modrinth: https://modrinth.com/mod/timeless-and-classics-zero)
- License: code GPL-3.0; assets CC BY-NC-ND 4.0 - no commercial, no derivatives, attribution.
  Internal test stand-in ONLY (weapon_data/tacz_ak47.tres default weapon).
  MUST be swapped out before any release.
- Conversion: tools/ai-gen/tacz_geo_to_glb.py (Bedrock geo + animation -> skinned GLB with 16 anims;
  magazine subtree split to separate centered GLB; CatmullRom baked to linear keyframes;
  position uses additive semantics).
- Verified: test_ads_calibration all green - rot_y=0, muzzle_local.z<0, rear/front sights
  project to exactly (960,540) in ADS.
- Serves as the "high-res voxel pixel style" reference: wood stock/handguard + metal + detachable mag.
## GodotSSRWater (river_water.gdshader SSR part, since 2026-08-10)

- Source: https://github.com/marcelb/GodotSSRWater
- Author: Marcel Bankmann
- License: MIT (see LICENSE.md in the repo); SSR ray-march + depth refraction
  adapted into assets/shaders/river_water.gdshader for the demo stream.
  （MagicaVoxel 制作，3884 面，含独立弹匣/枪机部件，最贴合"高精度体素像素风"）

## Poly Haven models (realistic vegetation, since 2026-08-10)

- Source: https://polyhaven.com/models (CC0 - no attribution required)
- Added: searsia_burchellii, shrub_01, flower_gazania, flower_heliophila,
  dandelion_01, grass_medium_02 (2k), tree_small_02 (1k)
- Downloader: tools/ai-gen/download_polyhaven.py
- Replaced cartoon Kenney props (mushroom_*, flower_*, crops_bambooStageB) removed 2026-08-10.