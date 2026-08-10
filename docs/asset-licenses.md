# 澶栭儴璧勪骇璁稿彲璇佽褰?
## _dl_ak47_adamkokrito.glb锛堝綋鍓嶄笅杞界増 AK-47锛?
- 鏉ユ簮锛歅oly Pizza https://poly.pizza/m/2zXzvGavqci
- 浣滆€咃細AdamKokrito
- 璁稿彲璇侊細CC-BY 3.0锛堥渶缃插悕锛?- 缃插悕瑕佹眰锛氫娇鐢ㄦ湰妯″瀷闇€娉ㄦ槑"AK47 by AdamKokrito (Poly Pizza), CC BY 3.0"
- 鐢ㄩ€旓細3-dfps 榛樿 AK-47 瑙嗘ā锛堜笅杞界増锛?- 2026-08-09 涓嬭浇锛涘凡閫氳繃 test_ads_calibration 鍏ㄧ豢锛堣嚜鍔ㄥ畾鍚?缂╂斁/鏈虹瀯鏍″噯/寮瑰專妫€鍑猴級

## akm_sketchfab_prep.obj锛堝綋鍓嶉粯璁ゆ鍣紝2026-08-09 璧凤級

- 鏉ユ簮锛歋ketchfab https://sketchfab.com/3d-models/akm-lowpoly-game-ready-b09ba6a7d56246adaff76ad091e4dc72
- 浣滆€咃細sami uddin锛園rameezuddin14锛?- 璁稿彲璇侊細CC Attribution锛圕C-BY锛夛紝闇€缃插悕
- 鍘熷涓嬭浇锛?1.9k tris / 11.3k verts / 4096脳4096 PBR 璐村浘锛圱extures/PBR 缁勶紝
  TGA 杞?PNG 2048 瀛樹簬 assets/models/ak/akm_sketchfab_tex/锛?- 棰勫鐞嗭紙tools/ai-gen/prep_akm_obj.py锛夛細鍓旈櫎鏃佺疆瀛愬脊閬撳叿銆乑鈫扻 杞銆佺煫姝?6掳 鍊炬枩銆?  褰掍竴鍖?1m銆佷繚鐣?UV 骞剁敓鎴?MTL 寮曠敤 PBR 璐村浘
- PBR 琛ヤ竵锛坱ests/export_pbr_mesh.gd锛夛細Godot OBJ 瀵煎叆鍙悆 albedo/normal锛?  閲戝睘/绮楃硻/AO 鎸夊懡鍚嶇害瀹氳ˉ鍏ュ苟瀵煎嚭 akm_sketchfab_pbr.tres锛堟父鎴忓紩鐢ㄦ璧勬簮锛?- 宸查€氳繃 test_ads_calibration 鍏ㄧ豢锛汫LM 璇勫锛歅BR 鍏ㄩ€氶亾鎺ュ叆鍚庢墦纾?6/10銆侀€犲瀷 7/10

## 澶囬€?
- _dl_akm_jtoastie.glb锛堝凡鍒犻櫎锛夛細Poly Pizza https://poly.pizza/m/52kQzphmeF 锛孞-Toastie锛孋C0锛?  璇勫閫犲瀷 4/10锛岃繃浜庢娊璞★紝2026-08-09 娓呯悊鏃ц祫浜ф椂涓€骞跺垹闄?- 浣撶礌鏂瑰悜鍊欓€夛細CGTrader AK74 Voxel Gun锛堝厤璐癸紝闇€娉ㄥ唽璐﹀彿涓嬭浇锛?  https://www.cgtrader.com/free-3d-models/military/gun/ak74-voxel-gun

## akm.glb parts version (default weapon since 2026-08-10)

- Source: user local E:\3d\Godot_v4.7.1-stable_win64.exe\新建文件夹\akm\akm.glb
  (FAB conversion; same Sketchfab AKM as akm_sketchfab_prep.obj: sami uddin, CC-BY, attribution)
- Parts: left/right gun halves + ejection + trigger + separate magazine; PBR 4K->2048 PNG
- Pipeline: tests/export_akm_glb.gd merges body / splits mag / normalize 1m / PBR -> ArrayMesh .tres
- Default weapon weapon_data/akm_glb.tres; test_ads_calibration green (auto muzzle/sights);
  GLM confirms complete & coherent, no fragments / floating pieces

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
  锛圡agicaVoxel 鍒朵綔锛?884 闈紝鍚嫭绔嬪脊鍖?鏋満閮ㄤ欢锛屾渶璐村悎"楂樼簿搴︿綋绱犲儚绱犻"锛?
## Poly Haven models (realistic vegetation, since 2026-08-10)

- Source: https://polyhaven.com/models (CC0 - no attribution required)
- Added: searsia_burchellii, shrub_01, flower_gazania, flower_heliophila,
  dandelion_01, grass_medium_02 (2k), tree_small_02 (1k), periwinkle_plant (2k)
- Downloader: tools/ai-gen/download_polyhaven.py
- Replaced cartoon Kenney props (mushroom_*, flower_*, crops_bambooStageB) removed 2026-08-10.
## AmbientCG ground textures (since 2026-08-10)

- Source: https://ambientcg.com (CC0 - no attribution required)
- Added 4K sets: Ground106 (forest floor leaves/mud), Ground092C (wet mud),
  packed to Terrain3D channel textures via tools/prepare_terrain_textures.gd.
