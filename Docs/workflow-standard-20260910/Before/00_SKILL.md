---
name: godot-3d-dev
description: 开发与维护 E:\3d 下的 Godot 4.7.1 3D 项目（目前是《无尽轮回》3D FPS 原型 3-dfps）。使用场景：用户提到 Godot / 3D FPS / E:\3d / 3-dfps、要把 AI 生成的 GLB/体素 OBJ 资产导入 Godot、搭 3D 场景或写 GDScript（含 Terrain3D 地形构造）、做骨骼动画/IK、跑无头验证或提交代码时。也适用于 UI/HUD/面板/换肤工作（autoload HUD、palette 主题、还原原项目 UI）、FPS 射击手感/武器/射击系统移植（参考 Unity FPS 项目把 recoil pattern、Hitbox 部位伤害、扩散惩罚、ADS、冲刺开火等移植成 GDScript）以及在 E:\3d 新建 Godot 3D 项目（每个项目独立 git 仓库）。
---

# Godot 3D 开发（E:\3d）

## 本项目后续转 UE5（2026-09-10）

用户指定 3D FPS 后续开发以 UE5 为主，当前工程 D:/FPS3D/FPSGAME/FPSGAME.uproject。新功能先确认引擎并使用对应 UE5 技能；本技能用于旧 Godot 原型维护及迁移参考。天气使用相邻 ue5-weather-workflow/SKILL.md。此约定仅针对本 FPS 项目，不改变其他 Godot 项目的技术选择。

## 环境

- 引擎（便携版，无安装）：`E:\3d\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe`
- 主项目：《无尽轮回》3D FPS → `E:\3d\3-dfps`（project.godot：Godot 4.7 / Forward Plus / Jolt）
- 新 3D 项目一律放 `E:\3d\`，每个项目独立 git 仓库。
- 项目惯例：主场景由 GDScript 代码搭建（`scripts/main.gd`），少手写复杂 .tscn，避免格式/属性名错误。

## 常用命令（PowerShell）

```powershell
$godot = 'E:\3d\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe'
& $godot --headless --path 'E:\3d\3-dfps' --import          # 新资产进来后重新导入
& $godot --headless --path 'E:\3d\3-dfps' --quit-after 120  # 跑 120 帧验证无脚本错误
```

## 资产管线（AI → Godot）

1. AI 生图 → TRELLIS.2（5080 的 ComfyUI）→ PBR GLB
2. 把 GLB 复制到 `assets/models/`，跑 `--import`
3. 代码里 `load("res://assets/models/xxx.glb").instantiate()`，挂到场景
4. 放置约定：TRELLIS GLB 脚底 y≈-0.21、头朝 +z；`position.y += 0.21*scale` 让脚落地

详细流程、黑狼参数与 three.js 原型对照见 [pipeline.md](references/pipeline.md)。

## 怪物标准工作流

原创怪物、2D 动作迁移、绑骨/蒙皮、怪物动作优化和战斗接入，使用相邻技能 [godot-monster-workflow](../godot-monster-workflow/SKILL.md)。用户要求先实际查看现有动画，再记录关键姿态与时间合同后制作。标准覆盖非常规拓扑，不强套类人骨架；完整案例见该技能 references/zombie-case.md。项目内同版位于 skills/godot-monster-workflow/。

## 敌人动画模型（现成资产路线）

- 用户接受通用替身时可优先选择 CC0 现成动画资产；用户指定原创身份、原图迁移或特殊拓扑时按怪物标准流程制作。过去黑狼 AI 试验未达预期，不代表所有原创怪物应放弃 AI 网格路线。
- 现役黑狼：`assets/models/wolf_quaternius.gltf`（CC0，12 条动画）+ `scripts/wolf_anim.gd`
  （AnimationPlayer 状态机，复用 enemy.gd 的 `rig_update` 契约，零改动接入）。
- 旧版备用僵尸：`assets/models/zombie_quaternius.glb`（CC0 Zombie Apocalypse Kit，16 条动画+Atlas 贴图，
  来自 `mars-tw/storm-apocalypse` 的 `public/models/zombie.glb`）+ `scripts/zombie_anim.gd`；
  `rig_update` 第 5 参 `chasing` 区分追击（Run_Arms）/游荡（Walk）。
- 来源：`SaadZiaatharKhan/Zoo`（ghfast.top）、quaternius.com 直连；itch/Meshy 被墙。
- 验收（数值化）：动画列表/蒙皮/头朝 +z/脚底 y/baseColorFactor/有无 UV/自包含。
- 改色 = 改 .gltf 的 `baseColorFactor`；无 UV 上不了贴图（资产固有限制）。
- 获取/验收清单/接入模式/改色/AI 路线踩坑存档（TRELLIS 碎面、朝向颠倒、UniRig 长链、
  GLTFDocument 导出坏骨架、混元 API 平台坑）全部见 [animated-enemies.md](references/animated-enemies.md)。

## 动画

- 制作每个动作前，先实际查看已有动作表或源视频，读取帧数、时长、循环、接触帧和状态机配置；记录关键姿态、重心、左右肢体差异及起势/接触/收势，再制作。缺少深度信息属于三维重建，不宣称自动精确还原。交付实际模型渲染预览及可编辑源文件/GLB，并核对导出时长、接触姿态与循环衔接。
- Godot 4.6+ 内置 IK：`SkeletonModifier3D` / `IKModifier3D`（TwoBone/Spline/FABRIK/CCD/Jacobian），做四足步态、落脚适配优先用它。
- 动画重定向：4.1+ 内置（SkeletonProfileHumanoid），Mixamo/API 动画导入后可直接重定向。
- three.js 原型已有黑狼 18 根骨骼程序化动画；移植用 `Skeleton3D` + `AnimationPlayer` / `AnimationTree`。
- GLB 里的骨骼动画 Godot 原生导入，无需 Blender。

### IK 解算（4.7 实测踩坑，2026-08-11）

换弹 IK 左臂（程序化 3 节骨骼+蒙皮，挂 Gun 下）**已于 2026-08-11 回滚删除**（观感不达标，用户要求撤掉），
仅保留纯弹匣动画（gun.gd 五段换弹）。踩坑记录如下，将来重做时参考。关键坑：

1. **`Skeleton3D.get_bone_global_pose()` 缓存默认是空的**（返回全零）→ IK 链坐标全为原点，报
   `The vectors must not be zero`（Quaternion.h）。建好骨骼后必须调 `reset_bone_poses()` 初始化缓存；
   无头模式下仅 `set_bone_global_pose_override(i, rest, 1.0, true)` 能喂进缓存。
2. **`IterateIK3D` 默认 `mutable_bone_axes=true` 读 bone POSE 原点**（只设 REST 时 POSE 原点恒零
   → 链长全 0 → 解算器静默跳过、骨骼纹丝不动）。只设 rest 的骨架要 `ik.mutable_bone_axes = false`。
3. **Modifier 的姿态写入只进蒙皮矩阵，不进骨骼 pose 数据**：`NOTIFICATION_UPDATE_SKELETON` 跑完
   modifier 后会把骨骼 pose 恢复成基底姿态。因此 `get_bone_pose*`/`get_bone_global_pose` 读不到 IK 结果，
   验证必须在 `modification_processed` 信号回调里观测，或看渲染图。
4. GDScript 4.7 没有 `float()` 构造器（`Nonexistent 'float' constructor`），用 `var x: float = obj.get(...)`。
5. 关节列表不用手动 `set_joint_count`：设 root/end 骨骼名后 `_update_joints` 自动填 root→end 链；
   配置顺序 `set_setting_count → root → end → target → rotation_axis`，`get_path_to` 需节点入树后调用。
6. **程序化蒙皮 `Skin.set_bind_pose` 必须存逆绑定矩阵**（`get_bone_global_rest(i).affine_inverse()`），
   直接存 rest 会把顶点变换两倍、全部甩出屏幕外——表现为"手臂隐形 / 换弹时一大块黑色盖住半屏"（实锤坑）。
   验证蒙皮是否正常：临时去掉 `mi.skin`/`mi.skeleton` 直接渲染同网格，可见则问题在 Skin。

## 射击手感 / 武器系统（Unity 参考移植）

- **枪械标准工作流入口**：新增武器、替换枪模、统一手模、调整装备/换弹、ADS、枪声、射击反馈或背包接入时，先读 [weapon-workflow.md](references/weapon-workflow.md)。涉及枪匠与配件时，继续读 [改造与 ADS 校准经验](references/gunsmith-ads.md)，按双标记对轴、套筒闭锁基准、镜片透明、活动挂点、原件替换与统一材质验收。仓库同版入口为 `skills/godot-weapon-workflow/SKILL.md`。这是本项目枪械开发的现行流程；下方静态网格与 TACZ 条目只适用于各自管线，不得用来归一化或去除带手臂动画资产的骨架。
- 参考仓库 `SakanakoChan/FPSGameBySakanako` 是 Unity/C#，只能移植设计/参数，不能直接搬代码；无 LICENSE 默认版权保留。
- 已沉淀到 3-dfps（anim 线提交）：部位伤害（`HitboxShape` 按 shape 索引倍率；enemy 自动从骨骼 head 生成 ×2 头部命中球，无骨骼退化为碰撞盒顶端）、弹道后坐力 pattern（固定序列 + 停火回退）、移动/空中扩散惩罚、冲刺开火延迟、贴墙 2m 弹道起点修正、`headshot` 信号、武器数据配置化（`WeaponData` Resource，`weapon_data/*.tres`，换枪=换 data）、粒子枪口火光（CPUParticles3D 三层：爆点/火舌/火星 + 软边光点 + 点光源）。
- 详细移植笔记（参数、实现要点、Godot 4.7 的坑）见 [gunplay.md](references/gunplay.md)。

## 技能 / 粒子特效移植（火球等）

- 两段式技能（凝聚 → 投掷）、命中判定与视觉分离（可以只保留射线判定、纯粒子火焰承担全部视觉）、
  三层火焰配方（白热内焰 / 黄焰主体 / 橙红外焰）、Godot 4.7 粒子 API 差异、渲染探针验证方法，
  全部沉淀在 [fireball-fx.md](references/fireball-fx.md)。
- 一句话防坑：粒子 `color_ramp` 必须配 `vertex_color_use_as_albedo = true`，否则粒子永远是白色——
  这是"火焰调来调去都是一团白"的根因（火球与爆炸粒子同样踩过）。

## 枪械视模接入与导入纪律（枪口方向 / 体素像素风）

换枪模 = 换 `weapon_data/*.tres` 的 `model_scene`（支持 PackedScene=GLB 或 Mesh=体素 OBJ/PLY），
`gun.gd` 启动时自动校准（朝向/缩放/瞄具/ADS/枪口点）。**每次导入新枪模必做：**

本节方向启发式、AABB 和弹匣拆分主要针对历史静态网格。带手模动画的新武器使用 [枪械标准工作流](references/weapon-workflow.md) 中的骨架适配、显式瞄具标记与实际视角验收；不得把特定模型的 `rot_y` 数值当成通用通过条件。

### 枪口方向判定（已内置，勿改回“细端=枪口”启发式）
- **默认枪口朝 +axis**（参考图 / TRELLIS / 混元 / 体素管线产物枪口均为 +X）；
- 仅当 -X 端出现“明确前准星立柱”（窄顶带 + 高度为照门 55%~90%）时才判定镜像（枪口 -X）；
- 自动判定仍误判时用 `muzzle_sign_override`（0 自动 / 1 / -1）强制指定，并在 .tres 里注明。
- **Sketchfab AKM（weapon_data/akm_sketchfab.tres）最终方向以玩家实测为准**：
  `muzzle_sign_override = -1`（180° 翻转，玩家确认）。翻转时必须**同步镜像瞄具锚点**
  到 -X：`sight_rear_override = Vector3(-0.02, 0.121, 0)`、
  `sight_front_override = Vector3(-0.325, 0.110, 0)`（镜像后 ADS 无 180° 翻转，rear_dist 正常；
  该高度经标记球+GLM 校准到真实瞄具，机瞄时照门/准星屏幕投影精确 = 屏幕中心）。
  启发式锚点会把机匣顶部误当照门导致瞄线下倾 10.5°，故一直用显式锚点（2.1°）。

### 数据驱动锚点（WeaponData 字段，全部 ZERO=自动检测）
- `sight_rear_override` / `sight_front_override`：照门/前准星锚点，**模型原始坐标**（与
  `_find_rear_sight` 返回值同坐标系）。显式锚点可避开启发式把机匣顶当照门的坑；
  枪口翻转（muzzle_sign 变号）时必须同步镜像锚点（x 取反），否则 ADS 求解会转 180°。
- `mag_offset`：独立弹匣中心（模型原始坐标）。Mesh+mag_scene 时弹匣节点是 _model 子节点
  （自带旋转/缩放），局部坐标用原始值，**不要**再乘 to_gun（会双重旋转/缩放）。
- 验证锚点精确度：`tests/probe_gun_projection.gd` 打印机瞄时 rear/front 的屏幕投影，
  应均 ≈ 屏幕中心（1920×1080 → (960,540)）。

### PBR 贴图管线（OBJ/MTL）
- Godot OBJ 导入器只读 albedo(map_Kd) + normal(map_Bump)，**不读 map_Pm/map_Ps/map_Ka**；
  需要 metallic/roughness/AO 时用 `tests/export_pbr_mesh.gd`（按贴图名前缀补通道，
  导出 ArrayMesh .tres，weapon_data 的 model_scene 指向 .tres）。
- 弹匣独立 surface（贴图名前缀 mag_）会由 export_pbr_mesh.gd 自动拆出为独立网格，
  配合 `mag_scene` + `mag_offset` 做真弹匣换弹动画（无黑块占位盒）。

### 十字准星 ADS 隐藏（已知坑）
- HUD.ensure_for_current_scene() 可能早于枪械创建执行（main._ready 先 ensure 后建枪），
  `_bind_scene` 找不到 Gun 会导致 ads_changed 永远连不上、准星不隐藏。
  已修：ui/hud.gd 拆出 `_bind_gun()` 并在未找到时 call_deferred 重试（≤300 帧）。
  换新场景若准星不隐藏，先查这个绑定时机。

### 换枪后必跑验证
```powershell
$env:GUN_TEST_MODEL='res://assets/models/xxx.glb'  # 或体素 .obj
& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_ads_calibration.gd
& $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_ads_view.gd
```
通过标准：`rot_y=±90` 且 `muzzle_local.z < -0.2`（枪口朝前）、照门/准星在相机光轴、无穿模；
渲染图里枪口应在左前、枪托右下。可加 `probe_gun_projection.gd` 打印投影坐标核对。

**标准武器添加工作流见 `E:\3d\3-dfps\docs\weapon-add-workflow.md`**（按步骤：模型来源/许可证 →
预处理 → 贴图 → 弹匣拆分 → 锚点/方向 → tres → 验证 → 提交）。
- **坑**：混元/体素模型的细端可能是枪托，细端法会把枪装反（“枪口在后”）；TRELLIS 中段机匣
  边缘也可能被误当准星。故一律按上面的“默认 +axis + 准星立柱证据”逻辑。

### 换枪后必跑验证
```powershell
$env:GUN_TEST_MODEL='res://assets/models/xxx.glb'  # 或体素 .obj
& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_ads_calibration.gd
& $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_ads_view.gd
```
通过标准：`rot_y=±90` 且 `muzzle_local.z < -0.2`（枪口朝前）、照门/准星在相机光轴、无穿模；
渲染图里枪口应在左前、枪托右下。可加 `probe_gun_projection.gd` 打印投影坐标核对。

### 体素 OBJ 纪律（tools/ai-gen/voxelize_glb.py）
- **顶点色必须写 0..1 浮点**（Godot 按浮点解析，写 0-255 会整枪发白）；
- **体素方盒六面必须外法线**（否则背面剔除→镂空/半透明，观感像“枪口反了”）：
  底面 `[1,0,3,2]`、顶面 `[4,5,6,7]`、前面 `[0,1,5,4]`、后面 `[2,3,7,6]`、左面 `[3,0,4,7]`、右面 `[1,2,6,5]`；
- **体素 Mesh 接入必须包一层 Node3D 父节点**（旋转/缩放设在父节点，MeshInstance3D 保持单位变换）：
  `_mesh_vertices` 会把 `mi.transform` 算进顶点；若 MeshInstance3D 自身带旋转，校准 `to_gun` 会再旋转一次
  → **双重旋转 → 枪口被转到身后**。此时校准测试会“自洽通过”但实际渲染是反的——
  必须用 `tests/render_gun_markers.gd` 标记球验证：红球=枪口应在画面左侧、蓝球=枪托在右侧。
- 输出 `.vox`（MagicaVoxel 精修）+ `.obj`（Godot 直连）；精度 `--pitch 0.005`=0.5cm（枪长~200 格）。
- `gun.gd` 对 Mesh 资源自动套“无光照 + vertex_color_use_as_albedo”材质（像素风）。

完整管线与 MagicaVoxel 精修步骤见 `E:\3d\3-dfps\docs\voxel-pipeline.md`。

## 地形构造（Terrain3D）

涉及旷野材质、植被或平滑体素挖掘时，先读 [可编辑旷野与材质调校](references/editable-wilderness.md)。仓库对应入口为 `skills/godot-terrain-vegetation/SKILL.md`；区分原高度图与 hole 查询、保持草土贴图配对，并按实机隔离水面/河床诊断。

成熟植被资产替换、FBX 多档 LOD 坐标归一、埋根和木质碰撞，先读 [植被接入](references/terrain-vegetation.md)。项目可发布版本位于 `skills/godot-terrain-vegetation/SKILL.md`。

- 插件：Terrain3D 1.0.2（`addons/terrain_3d`，MIT，GDExtension），`project.godot` 的 `[editor_plugins]` 已启用；支持 Godot 4.4–4.6+。
- 场景用 GDScript 代码搭建（参照 `scenes/demo_terrain.gd`），核心流程：
  1. `Terrain3D.new()` 加入场景，设 `data_directory`（空目录，区域文件运行时生成）
  2. 纹理：先跑 `tools/prepare_terrain_textures.gd` 把 AmbientCG PBR 打包成 Terrain3D 专用贴图（albedo alpha=高度、normal alpha=粗糙度，4096px；脚本自动优先 `{name}-4k/` 源，缺了回退 2K）；再 `Terrain3DAssets.set_texture(id, ta)`，`ta.uv_scale`≈0.05–0.15
  3. 高度图：`FastNoiseLite`（4.7 无 `TYPE_RIDGED`，用 `TYPE_PERLIN`）生成 1024² `Image.FORMAT_RF`，`region_size=512`，`data.import_images([img, null, null], pos, 0, scale)`，再 `data.save_directory()` 落盘
  4. 碰撞：`collision.set_mode(Terrain3DCollision.FULL_GAME)`（1km 地图足够；`DYNAMIC_GAME` 依赖活动相机）；RID 用 `get_rid().is_valid()` 检查
  5. 植被/岩石：`Terrain3DMeshAsset.scene_file` 指向 GLB，`instancer.add_transforms(id, xforms)` 批量散布，高度从 `data.get_height(pos)` 取
- 坑：
  - **Terrain3D 要求所有贴图集分辨率完全一致**——5 套 4096 + 4 套 2048 混用时地形网格静默不渲染（只有树/草/水可见，俯视是天空），日志报 `Texture ID N size ... doesn't match`；全量重出 4096 即恢复
  - 河流别用“绝对曲线+浅挖”：宏观地形 ±30m 时水面 y 会 -44~+38 摆动成碎块悬浮。正确做法=宏观降到 ±8m 缓丘 + 走廊内 blend 到一条缓坡河床线（`lerp(bed, macro, smoothstep)`），水面网格沿路径采样 `get_height+水深`，外缘顶点贴地（0 深度）+ 顶点色 alpha 渐隐做软岸线
  - 出生点必须在地表上方（Heightfield 单面，从下方/内部生成会掉穿，`y = get_height(pos) + 2`）；玩家 `collision_layer=4`，Area3D 传送门要 mask 全开再按名字过滤；TorusMesh 默认平躺，立式需 `rotation_degrees=(90,0,0)`
  - 渲染/截图脚本：场景内 Player 相机会在 ready 时抢 `current=true`，外部相机要 `_frames==25` 时重新 `_cam.current = true`，否则截到的是出生点视角（上半天、下半天）；Terrain3D 网格围绕活动相机生成，相机移动后等几帧再截图
  - Godot 4.7 CPUParticles3D 用 `mesh` 属性挂 QuadMesh（`draw_pass_1` 已废弃会报类型错）
  - GDScript 4 禁止同名变量遮蔽外层作用域（`_build_terrain` 里 `var t` 已有，循环内不能再 `var t`）
  - SurfaceTool **不自动生成法线**：无法线数组的网格用默认法线 (0,0,1) 水平朝 +Z，太阳从上方照到时 NdotL≈0 只有环境光，物体发灰；`generate_normals()` 又要求顶点数 %3==0（河床 574 顶点会失败）——自建水面/河床网格用 `set_normal(Vector3.UP)` 手动指定
  - 自定义三角形索引数必须是 3 的倍数（水面每段 12 个），否则 commit 报 `Vertex amount ... must be a multiple of 3` 且网格不可见；绕序不放心就 `cull_disabled`
  - 运行时创建的 ShaderMaterial/StandardMaterial `resource_path` 为空，按材质识别（如 `albedo_texture.resource_path`）而非 `mat.resource_path`
- 环境音：`tools/gen_river_ambience.py` 程序合成 12s 无缝流水循环（棕噪 120-1800Hz 水流 + 2.5-6.5kHz 水花 + 低频风），AudioStreamPlayer3D 挂河道；3D 音效必须给 Player 相机加 `AudioListener3D`。
- 完整配方、API、传送门与验证命令见 [terrain.md](references/terrain.md)。

## UI 线（HUD / 面板 / 还原原项目）

- 必须先读项目 `skills/godot-cold-steel-ui/SKILL.md`、`docs/cold-steel-ui-standard.md`、`UI-WORKFLOW.md`，再修改面板。当前冷钢规则优先于历史暗金主题说明。
- 普通UI用 Microsoft YaHei UI（TTC face 1）；物品名称用 SimHei，统一 `Style.make_item_name_font()` / `style_item_name()`；纯数字用 Consolas。标题用 `make_heading_font()`，不要组件单独调伪粗体。
- 六档字号24/20/16/14/12/11；普通面板最多四档。背包物品名12、装备名16是原布局例外。公共Theme必须指定RichTextLabel普通、粗体和等宽字体。
- 所有颜色消费公共Token。背包装备白色区、双手武器副手禁用等特殊样式照原组件CSS和业务代码，不凭主题变量推断。
- 先核对字体资源、face index、节点覆盖、字号、缩放、字重及阴影，再判断引擎渲染问题；同尺寸同状态截图验收。
- HUD数据继续由autoload管理；新面板使用容器、固定操作区、明确打开/关闭/拖放和保存合同。
- 历史架构和Godot踩坑见 [ui.md](references/ui.md)，当前执行标准以项目文件为准；推送按WORKFLOW第8节隔离混合历史。

## 注意事项

- `.godot/` 已在 .gitignore；`*.import` 与 `*.gd.uid` 必须提交。
- Godot 4 的 `ProceduralSkyMaterial` 没有 `sky_bottom_color`（那是 3.x），用 `sky_horizon_color` / `ground_horizon_color`。
- 改完场景/脚本必须跑无头验证（`--quit-after 120`），确认退出码 0 且无 SCRIPT ERROR。
- **资产建模纪律（换模型/重导出/拆件）**：
  1. 新资产一律先用**新文件名**独立生成并验证（几何检查 + 无头渲染），**验证成功后才覆盖正式文件名**；
  2. 不要中途删改 `.import` / `.tres` / 正式资产——会让项目引用缺失打不开（用户可能正在测试其他功能）；
  3. 置入顺序：候选验证 → 更新正式资产及引用 → `--import` → 对应管线校准与冒烟；保留导入设置，仅在证实单个资源缓存异常时定点处理，不例行删除 `.import` 或全库缓存。提交只包含归属明确且已授权的文件；
  4. Godot OBJ 导入会把网格归一化到原点（0..1.005），`gun.gd` 已按 AABB 反移居中；换网格后必跑校准测试；
  5. 部件拆分后验证弹匣区无残留（源 GLB `y<-0.05` 顶点=0；体素枪体只剩弹匣井自然底面）。
- 无头模式下 PointerLock/输入类报错可忽略，重点看 SCRIPT ERROR 与资源加载失败。
- 读/改中文 .gd 文件：PowerShell 用 `[System.IO.File]::ReadAllText`（`Get-Content` 按 GBK 显示乱码）；改文件用 apply_patch（相对路径从 cwd 出发，如 `..\..\..\3d\3-dfps\scripts\gun.gd`）。
- Godot 4.7 没有 `shape_owner_get_shapes()`；射线 `hit.shape` 索引按 CollisionShape3D 子节点注册顺序，倍率表按此顺序构建。
- 无头模式 `Skeleton3D.get_bone_global_pose()` 缓存不刷新：定位骨骼（如 head）用 `get_bone_global_rest()` 或手动 FK。
- GDScript：形参名不能遮蔽信号名（`headshot.emit()` 在形参也叫 headshot 时解析成 bool）；未类型化 Array 索引用 `:=` 推断报错，需显式类型。
- 新增 `class_name` 脚本后必须先 `--import`（注册全局类 + 生成 `.gd.uid`），再跑 `--quit-after`；`.gd.uid` 必须提交。
- 粒子坑（4.7 实测，完整配方见 [fireball-fx.md](references/fireball-fx.md)）：
  - 粒子 `color_ramp` 要生效必须 `StandardMaterial3D.vertex_color_use_as_albedo = true`，否则粒子用材质白色；
  - 粒子尺寸 = draw_pass quad 尺寸 × scale，放大要两头一起动；
  - `turbulence_noise_speed` 是 **Vector3**（写 float 编译报错）；
  - `scale_curve`（CurveTexture）替代 3.x 的 `scale_curve_min/max`，用 `CurveTexture.curve = Curve` 包一层；
  - 火焰层次用 MIX 主体 + ADD 火星/光晕，避免 ADD 叠加过曝成白团；
  - 悬浮阶段不用 RibbonTrailMesh（上下浮动会渲染成竖柱），飞行尾迹用世界空间粒子点排布；
  - shader 的 `EMISSION` 不经过 alpha，要"隐形球体"必须同时大幅降低 EMISSION；
  - 粒子挂硬边方块贴图会显颗粒感，用程序生成软边径向渐变贴图（`a=(1-d)^2`）。

## 并行开发工作流（动画线 ↔ UI 迁移线）

仓库同时有两条开发线，靠文件所有权 + 提交纪律并行，**不建 git 分支**，完整约定见项目根 `WORKFLOW.md`。核心规则：

- 动画线：`enemy.gd` / `enemy_models.gd` / `projectile.gd` / `gun.gd` / `player.gd`（动画相关）/ `assets/models/`
- UI 线：`ui/`、`scenes/ui/`、`assets/ui/`、`project.godot`、`main.gd` 的 HUD 部分
- `main.gd` 是唯一共享文件：动画线只改场景搭建/敌人配置，UI 线只改 `_build_hud` 与 `_on_*` 处理
- 改前 `git status` 确认对方没未提交改动；改完立即提交（`anim:` / `ui:` 前缀）；提交前跑无头验证
- 稳定契约（UI 数据源，禁止改签名）：`player.gd` 的 `damaged`/`died`/`hp`/`take_damage`；
  `gun.gd` 的 `shot`/`hit`/`reloading`/`reloaded`/`empty`/`ammo`/`reserve`；`enemy.gd` 的 `take_damage`

## TACZ / 基岩模型导入管线（Minecraft 模组 → Godot 枪械）

用户要把《永恒枪械工坊》(TACZ) 当**风格基准 + 内部测试替身**时走这条管线：

- 下载：Modrinth API `https://api.modrinth.com/v2/project/timeless-and-classics-zero/version`，
  国内走 GitHub 镜像 fork 的 release（如 MUKSC/TACZ-1.21.1）+ `ghfast.top` 加速。
- 解包 JAR（ZIP）后枪模在 `assets/tacz/custom/tacz_default_gun/assets/tacz/`：
  `geo_models/gun/<枪>_geo.json`（基岩 1.12.0 几何）+ `animations/<枪>.animation.json`（基岩 1.8.0 动画，
  大量 CatmullRom）+ `textures/gun/uv/<枪>.png`（+`_n` 法线 +`_s` 高光）+ `display/guns/*_display.json`。
- 转换：`tools/ai-gen/tacz_geo_to_glb.py` → 带骨骼/动画 GLB + 独立弹匣 GLB。
  关键语义（已对 Blockbench 源码核对）：方块原点=绝对模型坐标；骨骼节点 TRS=T(p−R·S·p,R,S)，
  静止时恒等、bind=identity；动画 position 用 **additive**（pivot+偏移）；旋转 XYZ 欧拉；
  面表/UV 按 Blockbench `getVertexIndices` 反序（glTF 外向法线）；CatmullRom 烘焙为线性关键帧。
- **导入游戏前必须 `--normalize-length 1.0 --center`**（枪模转进 Godot 必做）：
  gun.gd 视模缩放 `clampf(VIEWMODEL_LENGTH/extent, 0.4, 1.0)` 有下限、且 GLB 路径不像 Mesh
  路径那样自动 `mi.position=-AABB_center` 居中。像素单位模型（TACZ 全长 ~43）不归一化会被
  放大成 17m 巨物、不居中的网格会整体偏高/枪托贴相机被近平面切掉 → 实测表现为"破碎感、
  看不出是枪"。转换器会打印 `body AABB center`，把它从瞄具锚点与 `mag_offset` 中减掉。
- **贴图两坑**：① Minecraft 模组 PNG 常带"全零 alpha"（Minecraft 忽略、Godot 按透明渲染 →
  枪变碎块），转换器自动剥 alpha；② TACZ 黑金属贴图过暗，需 gamma 提亮+抬升暗部
  （`(v/255)^0.55*1.25+42`），否则黑枪在深背景上只剩零星高光、"破碎感"。
- **弹匣居中坑**：弹匣 GLB 顶点减**弹匣自身 AABB 中心**，`mag_offset` 才是
  mag_center−body_center。把 offset 误减进顶点会让弹匣整体高 body_center.y、浮在机匣里，
  表现为"弹匣缺失/错位"。
- **Godot 导入缓存会卡死**：同文件名反复重导可能一直用旧资源（.import/.scn 哈希不变、
  渲染直方图纹丝不动）。遇到"改了没反应"直接**改文件名**（ak47_v3.glb）强制全新导入，
  同步更新 .tres，再清理旧文件与孤儿提取贴图。
- **TACZ/基岩枪模最终路线：静态 ArrayMesh，不走骨骼 GLB**（2026-08-10 实测）：骨骼 GLB
  在 Godot 渲染持续"破碎"，但同一几何导出 OBJ 渲染是完整 AK——问题在 GLB 骨骼导入路径，
  不在几何/法线。办法：`tacz_geo_to_glb.py --normalize-length 1.0 --center` 只作中间源，
  `tests/export_tacz_mesh.gd` 转成静态 ArrayMesh .tres（去 ARRAY_BONES/WEIGHTS，挂提亮贴图），
  weapon_data 用 Mesh 路径（gun.gd 自动居中+mag_offset）。骨骼动画暂弃，程序化动画已够用。
- **体素"破碎感"终极处理**：模型正确后剩余的碎感来自方块接缝 + 逐块光照斑块。
  转换时 `--inflate 0.002`（闭合发丝缝）+ `--face-ao 0.9`（烘焙方块边缘 AO：每面拆中心顶点，
  角 0.9 中心 1.0 顶点色，export_tacz_mesh.gd 材质开 vertex_color_use_as_albedo）。
  0.74 过暗，0.9 合适。
- 弹匣：`--split-bone magazine` 拆出子树并**按 AABB 中心居中**，输出值作 `mag_offset`。
- 锚点（模型原始坐标实测）：枪口=AABB min-z 端顶点；照门/准星=iron_sight3/4 方块簇顶部中心。
- **gun.gd 坑**：TACZ 主轴向 Z（axis==2）且枪口在 −Z，`_calibrate_viewmodel` 的 Z 轴分支旋转
  已修正为 `rot_deg = 180.0 if sign>0 else 0.0`（旧代码反了，会把枪口转到背后）；
  `muzzle_sign_override=-1` + 显式瞄具锚点最稳。GLB 弹匣：`mag_scene` 支持 PackedScene 分支
  （`mag_scene is PackedScene`），节点挂 `_model` 子节点、位置=mag_offset。
- **导入缓存坑**：Godot `--headless --import` 对"之前失败过、内容又变"的文件可能不重导，
  表现为 `.import` 仍 `valid=false`。遇到先删该文件的 `.import` + `.godot/imported/<hash>.md5`
  再导入（PowerShell 删被策略拦时用 python os.remove）。
- 验证：`test_ads_calibration.gd` 已放宽 rot_y ∈ {0,±90,180}；ADS 照门/准星投影须 =(960,540)。
- 许可证：TACZ 资产 CC BY-NC-ND 4.0 —— 只做非商用测试替身，发布前换掉，记录在
  `docs/asset-licenses.md`。

## 昼夜、天气与事件预报

该项目天气开发先读 `E:/3d/3-dfps/skills/godot-weather-workflow/SKILL.md`，按对应标准工作流扩展确定性调度、云光、雨雷音效及事件进度栏。保留原进度条，连续降雨只作为一个当前/最近事件。

## 改造件无间隙装配

制作或调整枪械配件时必读[无间隙装配合同](references/attachment-fit.md)。用户要求组件与枪身、组件内部应接触部位不得留可见间隙；按实际网格逐枪校验，不照搬其他枪挂点，不用穿插或改变光照掩盖问题。

## 前握把动作与材质正式接入

侧斜握把、装备回握和材质候选正式接入，阅读[专项复查](references/foregrip-material-integration.md)。

## 分区聚合物与小砖点缀（2026-09-07）

新武器模型及新改造件默认按[聚合物设计语言与材质标准](references/polymer-style.md)执行：连续枪体、稀疏精细小砖、分区聚合物、无做旧与碳纹。逐枪校准分区，逐件检查连接、装卸恢复、骨骼跟随、镜片和游戏/预览一致性。


## 武器材质表现升级（2026-09-09）

以后新枪及材质优化默认执行[武器材质表现标准](references/surface-detail-standard.md)：保留当前分区风格，恢复可用原生法线和受控粗糙度，区分机械金属与聚合物；正式资源自包含，游戏/预览/图标统一，并验证装卸恢复、动作、ADS及目标 GPU。本文较早的粗糙度或法线起点以新标准的逐部位校准为准。用户已授权的候选替换直接完成接入，不重复要求批准。


完成武器及配件材质升级后必须执行[游戏实际材质应用审计](references/material-activation-audit.md)：逐可见表面检查最终材质，覆盖迟创建部件、整件覆盖、缓存切枪、全变体和新进程读档，并用故意回退单表面的测试验证漏报。

武器 shader 唯一正式目录为 assets/materials/weapon_surface_detail/。旧材质与旧环境回退开关已移出项目；每次材质修改先运行 tests/test_weapon_material_single_source.gd，再做全表面、实际场景和新进程读档检查。
