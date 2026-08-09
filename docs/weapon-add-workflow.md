# 武器添加标准工作流（3-dfps）

目的：新增一把武器（GLB/OBJ）到游戏的标准步骤，含预处理、贴图、弹匣拆分、
瞄具锚点、方向、验证与提交纪律。全部坑都来自 AKM 接入实战（2026-08-09）。

## 总览

模型来源/许可证 → 预处理（转正/剔道具/居中）→ 贴图（PBR）→ 弹匣拆分 →
瞄具锚点 + 方向（玩家实测）→ weapon_data/.tres → 验证清单 → 提交

## 0. 前置纪律

- 新资产一律**新文件名**独立生成并验证，**通过后才覆盖正式文件**；不要中途删
  `.import`/`.tres`/正式文件（引用错误会让项目打不开）。
- 文件所有权：动画线动 `scripts/gun.gd`、`weapon_data/`、`assets/models/`、`tools/ai-gen/`、
  `docs/`、`tests/`；**不碰** `ui/`（除用户明确要求）、`project.godot`、`DESIGN.md`。
- 每个武器独立提交，`anim:` 前缀，只 `git add` 自己的文件。

## 1. 模型来源与许可证

- 免费可直链：Poly Pizza（CC0/CC-BY）、OpenGameArt（CC0）、Sketchfab（CC-BY，需账号）、
  CGTrader 免费区（需账号）。国内可达：混元3D API（tools/ai-gen/hunyuan3d_api.py）。
- **Sketchfab 下载包是 zip，别只解压 OBJ**——里面还有 `.mtl` + `Textures/PBR`（TGA 4096²）。
- 下载后把来源/作者/许可证/署名要求记入 `docs/asset-licenses.md`（CC-BY 必须署名）。
- 先检查模型质量：tri 数、是否带贴图、有无独立道具/多部件。

## 2. 预处理（模板：tools/ai-gen/prep_akm_obj.py）

```powershell
python tools/ai-gen/prep_akm_obj.py --input assets/models/ak/xxx.obj `
  --out assets/models/ak/xxx_prep.obj --mtl assets/models/ak/xxx_prep.mtl `
  --tex-dir assets/models/ak/xxx_tex
```

- **剔道具**：独立"子弹/备用弹匣/支架"等组（与主枪体 AABB 不相交）剔除。
- **转正**：长轴 → X（Z→X 旋转），矫正倾斜（y-x 斜率），归一化到枪长 1m（gun.gd 缩放才合理）。
- **居中**：只用保留部件计算 AABB 中心（把被剔除道具算进去会 z 偏心 2cm+）。
- **方向**：端标记铁证（+X 红球 / -X 蓝球 + GLM 读"木托端在哪"），**最终方向以玩家实测为准**，
  不要用"细端=枪口"这类启发式跟玩家争（AKM 实战教训：启发式把方向搞反了）。
- 输出：贴图模式（保留 UV + MTL）或顶点色模式（无贴图兜底）。

## 3. 贴图（PBR）

- TGA → PNG 2048（PIL），命名：`akm_basecolor/normal/roughness/metallic/ao.png`；
  弹匣独立材质用 `mag_*` 前缀（export 工具按前缀识别拆分）。
- **Godot OBJ 导入器只读 albedo(map_Kd) + normal(map_Bump)，不读 metallic/roughness/AO**：
```powershell
$env:PBR_MESH='res://assets/models/ak/xxx_prep.obj'
$env:PBR_OUT='res://assets/models/ak/xxx_pbr.tres'      # 枪体（含 PBR 通道）
$env:PBR_MAG_OUT='res://assets/models/ak/xxx_mag.tres'  # 独立弹匣（可无）
& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/export_pbr_mesh.gd
```
- 材质验证：`tests/tmp_probe_mat.gd` 模式（albedo/metallic/roughness/ao 全非空）。

## 4. 弹匣拆分（有真弹匣则必做）

- `mag_scene` = 弹匣 .tres；`mag_offset` = 弹匣面 AABB 中心（模型原始坐标）。
- 弹匣节点是 `_model` 子节点（自带旋转/缩放），局部坐标**用原始值，不要再乘 to_gun**
  （会双重旋转/缩放）。
- 不接 mag_scene 时 gun.gd 会在弹匣位生成**深色占位盒（黑块）**——玩家会投诉。

## 5. 瞄具锚点 + 方向

- 测照门/前准星模型坐标：顶点顶部剖面（细高凸起）+ 标记球 + GLM 校准高度
  （锚点偏高会机瞄低头/觇孔不重合）。
- `sight_rear_override` / `sight_front_override`：模型原始坐标，ZERO=自动检测。
  **自动检测会把机匣顶当照门（瞄线下倾 10.5°）**，故建议显式锚点（2.1°）。
- `muzzle_sign_override`：以玩家实测为准；**翻转时必须同步镜像瞄具锚点（x 取反）**，
  否则 ADS 求解会转 180°（rear_dist 触底 0.38、机瞄画面反转）。

## 6. weapon_data/xxx.tres

- 从 `weapon_data/akm_sketchfab.tres` 复制参数模板，改：`weapon_name`、
  `model_scene`、`mag_scene`、`muzzle_sign_override`、`sight_*_override`、`mag_offset`。
- 默认武器切换：`scripts/gun.gd` 的 `@export var data` preload + `_setup` 兜底 load
  两处改成新 tres（或告知用户切换方法）。

## 7. 验证清单（全部通过才算完成）

```powershell
$env:GUN_TEST_MODEL='res://assets/models/ak/xxx_pbr.tres'
& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_ads_calibration.gd
# 通过标准：rot_y=±90、muzzle_local.z<-0.2、ads_rot 无 ±180° yaw、rear_dist∈[0.38,0.75]

& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/probe_gun_projection.gd
# ADS 时 rear/front 屏幕投影均 ≈ 屏幕中心（1920×1080 → 960,540）

& $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_gun_markers.gd
# 红球(枪口)画面左侧、蓝球(枪托)右侧

& $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_ads_view.gd
& $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_reload_frame.gd
# 腰射/机瞄/换弹中段渲染：无黑块、真弹匣滑出、觇孔重合

& $godot --headless --path 'E:\3d\3-dfps' --quit-after 90
# 无 SCRIPT ERROR；注意其他线未提交 WIP 可能阻断冒烟（先 git status 确认）
```

- 十字准星 ADS 隐藏：HUD 绑定时机（ui/hud.gd `_bind_gun` 延迟重试）已修复；
  新场景若准星不隐藏先查绑定。

## 8. 提交

- `git add` 只加自己的文件（新 OBJ/GLB、.import、tres、贴图、脚本、文档、预览图、许可证记录）。
- `anim:` 前缀，commit message 写清：模型来源/许可、预处理、锚点/方向、验证结果。

## 相关脚本速查

| 工具 | 作用 |
| --- | --- |
| tools/ai-gen/prep_akm_obj.py | OBJ 预处理（转正/剔道具/居中/UV+MTL 或顶点色） |
| tools/ai-gen/voxelize_glb.py | GLB → 高精度体素（体素风） |
| tools/ai-gen/voxel_ak_builder.py | 程序化手搭体素 AK（体素风，已搁置） |
| tests/export_pbr_mesh.gd | OBJ 补 metallic/roughness/AO，导出 .tres（枪体/弹匣分离） |
| tests/test_ads_calibration.gd | ADS 校准回归 |
| tests/probe_gun_projection.gd | 打印照门/准星/枪口屏幕投影 |
| tests/render_gun_markers.gd | 方向标记球渲染 |
| tests/render_ads_view.gd / render_reload_frame.gd | 第一人称腰射/机瞄/换弹渲染 |
