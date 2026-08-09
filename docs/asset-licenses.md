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
- 原始下载：21.9k tris / 11.3k verts / 4096×4096 PBR 贴图（本仓库仅收到 AKM.obj，
  无 MTL/贴图；由 tools/ai-gen/prep_akm_obj.py 预处理为 X 轴 + 顶点色 OBJ，按部位上色）
- 预处理：剔除旁置子弹道具、Z→X 转正、矫正 6° 倾斜、归一化 1m、木/钢/弹匣上色
- 已通过 test_ads_calibration 全绿；若补上原 PBR 贴图可升级打磨分

## 备选

- _dl_akm_jtoastie.glb（已删除）：Poly Pizza https://poly.pizza/m/52kQzphmeF ，J-Toastie，CC0；
  评审造型 4/10，过于抽象，2026-08-09 清理旧资产时一并删除
- 体素方向候选：CGTrader AK74 Voxel Gun（免费，需注册账号下载）
  https://www.cgtrader.com/free-3d-models/military/gun/ak74-voxel-gun
  （MagicaVoxel 制作，3884 面，含独立弹匣/枪机部件，最贴合"高精度体素像素风"）
