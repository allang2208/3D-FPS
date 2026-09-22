# SVD（德拉贡诺夫狙击步枪）导入

用户指定的 [Sketchfab 模型](https://sketchfab.com/3d-models/svd-dragunov-sniper-rifle-2ac78fb5a0eb40f5a02a5b0a9f566abf)（作者 **LeroyCake**，**CC BY 4.0**）的下载、机械分件与导入。

**当前状态：枪体 4 件 + PSO-1 瞄具 3 件已分件并导入；还不是可在游戏中使用的武器。**

- 完整接入记录（含现有武器骨架侦察与剩余步骤）：[Docs/Weapons/svd-import-20260922.md](../../Docs/Weapons/svd-import-20260922.md)
- 来源、许可、散列与改动说明：[PROVENANCE.md](PROVENANCE.md)
- 署名声明：[ThirdPartyNotices/SVD_DRAGUNOV.md](../../ThirdPartyNotices/SVD_DRAGUNOV.md)

## 已导入（`/Game/Weapons/SVDDragunov20260922`）

八个部件**共用同一坐标原点**，摆同一变换即为整枪装配：

| 网格 | 三角面 | 尺寸 (cm) | 材质实例 | 对应目标骨骼 |
| --- | --- | --- | --- | --- |
| `SM_SVD_Body` | 19,252 | 3.73 × **122.5** × 17.80 | `MI_SVD_Body` | `WPN_root` |
| `SM_SVD_Magazine` | 4,936 | 2.67 × 10.07 × 10.03 | `MI_SVD_Magazine` | `WPN_SOCKET_Magazine` |
| `SM_SVD_Trigger` | 428 | 1.78 × 1.87 × 3.13 | `MI_SVD_Trigger` | `WPN_Trigger` |
| `SM_SVD_ChargingHandle` | 96 | 2.21 × 2.01 × 0.63 | `MI_SVD_ChargingHandle` | `WPN_ChargingHandle` |
| `SM_SVD_SafetyLever` | 728 | 0.61 × 10.88 × 3.54 | `MI_SVD_SafetyLever` | （骨架无对应骨骼，独立件保留） |
| `SM_SVD_ScopeBody` | 3,859 | 7.64 × 30.69 × 13.74 | `MI_SVD_ScopeBody` | 瞄具挂点（待标定） |
| `SM_SVD_ScopeMount` | 1,835 | 3.04 × 15.29 × 7.69 | `MI_SVD_ScopeMount` | 镜座（可换装） |
| `SM_SVD_ScopeLens` | 355 | 4.05 × 30.05 × 4.05 | `MI_SVD_ScopeLens` | —（镜片组，无碰撞） |

贴图 10 张 4096²（`svd_*` 与 `pso_*` 两套）；Nanite 关闭；实体件三角面碰撞。

## 分件方式（未裁切表面）

源枪体 758 个壳体、瞄具 228 个壳体，机械件与主体混在一起。分件按**测量区域重组既有壳体**，不裁切任何表面，因此每个部件保持闭合、UV 与法线不变，**面数总和 31,489 与源一致**：

| 部件 | 判定区域（源坐标） | 壳体数 |
| --- | --- | --- |
| 弹匣 | y∈[−0.270,−0.130]、z≤0.125、x∈[0.140,0.190] | 53 |
| 扳机 | y∈[−0.300,−0.255]、z∈[0.055,0.100] | 17 |
| 拉机柄 | 凸出到 x≥0.198 | 5 |
| 保险／快慢机 | x≥0.185、z∈[0.125,0.160]、x 向薄 | 20 |
| PSO-1 镜座 | x≤0.156 且 z≤0.23（镜筒轴线 z≈0.259 的左下） | 97 |
| PSO-1 镜片组 | 沿 Y 零厚度、圆形（长短径差≤6 mm）、居中于镜筒轴线 | 11 |

区域来自三步定量证据：`Scripts/color_shells.py` 与 `Scripts/analyze_scope_shells.py`（最大壳体上色渲染定位）、`Scripts/list_lower_shells.py`（列出所有"挂在机匣下方／右侧凸出"的壳体），最后由 `Scripts/separate_svd_parts.py` 分件并出彩色验证图 `Previews/mechanical/`（含 `scope_side`、`scope_front` 瞄具特写）。

## 目录

| 路径 | 内容 |
| --- | --- |
| `Config/svd.json` | 模型来源、许可、实枪尺寸、本轮范围 |
| `Config/import_spec.json` | 导入唯一数据源：八个部件、材质槽→贴图组、命名与压缩策略 |
| `Source/` | `svd_source.glb`（几何来源）与解包后的原包（`model.dae` + 10 张 4096 原图） |
| `Authored/` | 八个 `SM_SVD_*.fbx`（枪体 5 + 瞄具 3）、`SVD_Mechanical.blend`（分件场景）、`SK_SVD_Viewmodel.blend`（装配 + 手臂）、`SK_SVD_Manny.fbx` |
| `Textures/` | 10 张 4096²（法线为无损 PNG） |
| `Previews/` | 源四视图、机匣特写（`receiver/`）、壳体上色（`shells/`）、瞄具壳体（`scope_shells/`）、分件验证（`mechanical/`）、持握调查（`arms_ref/`、`hold/`） |
| `Receipts/` | `download` / `source_scan` / `body_islands` / `shells_below` / `shell_colors` / `scope_shells` / `parts` / `textures` / `import` / `verify` / `weapon-recon` / `skeleton_recon` / `alignment` / `hold_reference` / `magazine_contact` / `rig` / `viewmodel_import` / `viewmodel_verify` / `asset_resolution` / `material_*` / `roll_vs_m4` 等 |

## 已归档的废案（trash，本地）

按 WORKFLOW.md 第 4 节，四项被取代的文件已移入 `trash/svd-dragunov-superseded-20260923/`（含 MANIFEST.json 记录原路径、大小、SHA-256、原因与替代物）：

| 原路径 | 替代物 |
| --- | --- |
| `Scripts/prepare_svd.py` | `separate_svd_parts.py`（枪体分件 + 瞄具分件）+ `prepare_textures.py` |
| `Authored/SVD_Editable.blend` | `Authored/SVD_Mechanical.blend` |
| `Authored/SVD_Aligned.blend` | `Authored/SK_SVD_Viewmodel.blend`（同一放置 + 共享手臂 + 刚性绑定） |
| `Authored/SM_SVD_Scope.fbx` | `SM_SVD_ScopeBody` / `ScopeMount` / `ScopeLens`（UE 资产已通过资产 API 退役） |

## 绑手臂的准备（已完成测量，未接入）

- **绑定姿势不是持枪姿势**：M4 的 `SK_M4_FoldingSights_HK416.fbx` 在 rest pose 下武器同样浮在手臂上方（手臂中心 z≈−0.42），该姿势不能作为握持判据。
- **真正参照是动画里的手位**：从项目现成的 `A_AKM_idle.fbx`（同一套 Manny 手臂与 `WPN_*` 骨骼）中段采样，相对 `WPN_root` 得到右手握持区 y∈[−0.110, +0.065]、左手支撑区 y∈[+0.193, +0.308]、枪口挂点 y=+0.586。
- **SVD 放置**（`Scripts/align_to_arms.py`）：两枪同向（扳机与弹匣都在握把前方），只做平移、不旋转；握把对齐误差 0.0 mm，扳机残余 3.7 cm、膛线低 4.0 cm（两枪握把→扳机几何不同，刚体变换无法同时满足）。扳机指位与开镜眼距留到实际持枪姿势里标定。
- 对齐结果写入 `Receipts/alignment.json` 与 `Receipts/hold_reference.json`，装配场景为 `Authored/SK_SVD_Viewmodel.blend`。

## 待办：材质重建排队中

为修正材质命名而在编辑器加载着资产时删了磁盘 `.uasset`，导致编辑器内包变脏、后续导入被守卫拦下；`Materials/` 目前是半成品（Body/Magazine/Trigger 正常，ChargingHandle/SafetyLever 只有错名母材质，瞄具三件材质缺失）。干净重建已排队，等占用编辑器的会话释放后自动执行；网格侧 8 件已在盘上。

## 视图模型（已绑定共享手臂）

`/Game/Weapons/SVDDragunov20260922/Viewmodel/SK_SVD_Manny` —— 手臂 + SVD 八件合一的骨骼网格，**复用 M4 骨架** `/Game/Weapons/M4HK416Replica/SK_M4_HK416_Skeleton`：

| 项 | 值 |
| --- | --- |
| 组成 | 共享 Manny 手臂 20,326 顶点 + SVD 八件 25,195 顶点，LOD0 **52,189 顶点** / 10 sections |
| 骨骼绑定 | Body→`WPN_root`、Magazine→`WPN_SOCKET_Magazine`、Trigger→`WPN_Trigger`、ChargingHandle→`WPN_ChargingHandle`；SafetyLever 与瞄具三件→`WPN_root` |
| 材质 | 10 槽全映射；手臂两槽复用 M4 当前 `MI_Manny_01/02`，八件各用 `MI_SVD_*`（父级已全部校验） |
| 尺寸校验 | 包围盒 `[110.87, 122.5, 77.47]` cm——X 向与 M4 **完全相同**（同一副手臂），Y 向即 SVD 全长 |

绑定脚本 `Scripts/rig_svd_viewmodel.py`（Blender）、导入 `Scripts/import_svd_viewmodel.py`、读回 `Scripts/verify_svd_viewmodel.py`。

## 开镜与接触点标定（已测，未接入）

| 项 | 值 |
| --- | --- |
| PSO-1 光轴（武器空间） | 目镜面 `(1.86, −38.93, 9.42)`、物镜端 `(1.86, −8.89, 9.42)` cm |
| 建议 `ADSRearEyeDistance` | **7 cm**（实镜出瞳 68 mm；M4/QBZ 12、ASH-12 18） |
| 扳机指位残余 | **1.49 cm**（动画食指指尖 vs SVD 扳机中心，AKM idle 实测） |
| 枪口相对共享 `WPN_SOCKET_Muzzle` | `(4.38, **70.25**, −7.59)` cm，距离 **70.79 cm** ⚠ |

⚠ **共享枪口挂点是按 M4 长度放的**：M4 只需 4.84 cm 后偏、ASH-12 是 6.79 cm，而 1.225 m 的 SVD 真实枪口在该挂点前方 70.25 cm、下方 7.59 cm——**枪口烟火/曳光不能复用 M4 的偏移量**。

测量已写成 `Source/FPSGAME/Weapons/SVDWeaponAssets.h`（每枪一个参数头的项目约定），**该头文件未被任何 cpp 包含，编译不变**；接入要改 `FPSGAMECharacter.cpp` 分支并做完整 Editor 构建。

## 武器接入（代码 + 数据 + 图标已完成，**待编译**）

| 项 | 内容 |
| --- | --- |
| 参数头 | `Source/FPSGAME/Weapons/SVDWeaponAssets.h`（路径、瞄点、出瞳 7 cm、枪口偏移、`Matches()`） |
| 角色代码 | `FPSGAMECharacter.cpp`：武器分支 + ADS 标定分支 + 三处触发路径；`FPSGAMECharacter.h`：`bSingleShotTrigger` / `UsesSingleShotTrigger()` |
| 白名单 | `FPSGAMECharacterProfile.cpp` 加入 `ue_svd` |
| 数据 | `items.json` / `gunsmith.json` / `combat-weapon-formulas.json` 各一条；弹药沿用 `ammo_pkm_762x54r`（7.62×54R LPS） |
| 图标 | `Content/ColdSteelData/Icons/ue_svd.png` + `ue_svd.uasset`（768×320 透明朝左，设置对齐 `ue_m4a1`） |
| 动画/音效 | 复用 M4 剪辑集与 HK416 套件（`bUsingM4Infima`）；**弹匣接触点与 M4 相差 1.2 cm**，可直接复用 |
| 编译 | **已通过**：`Build-Editor.ps1` 127/127 Succeeded（68.6 s） |
| 接线解析 | **`ok: true`，无缺失**：7 条剪辑 + 5 条音效 + 视图模型 + 图标全部按代码路径载入；idle／开火剪辑在 `SK_M4_Infima_Skeleton` 上属**已声明的兼容骨架**，合法 |

## 实机反馈修复（2026-09-23）

| 症状 | 根因 | 状态 |
| --- | --- | --- |
| 第一人称是灰白/棋盘格 | 八个 `MI_SVD_*` **缺 SkeletalMesh 用途标记**（Python 新建材质没勾），UE 回退默认材质。日志原文：`missing usage flag SkeletalMesh! Default Material will be used` | **已修**：从 M4 现用材质抄用途标记，`all_ok: true` |
| ADS 枪身侧倾 | 三种口径互相矛盾（面积加权 3.04°、窄带对 SVD 恰好 0.000°、**PCA 仅 0.658°**）。面积加权被斜护木/贴腮板带偏 | **已撤回**先前的 3.04° 反向滚转（`applied_angle_deg = 0.0`）；运行时标定读数证明轴向与眼距公式都正确 |
| 换枪后半自动粘滞 | `bSingleShotTrigger` 只在 SVD 分支赋值、不复位 | **已修**：改在 `InitializeWeaponVisuals` 开头统一复位，已重编译 |

诊断脚本：`Scripts/fix_material_usage_flags.py`、`Scripts/measure_roll_vs_m4.py`、`Scripts/diagnose_materials.py`。

## 脚本与复现

```powershell
$bl = 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
$case = 'D:\FPS3D\FPSGAME\SourceAssets\SVDDragunov20260922'

$env:SKETCHFAB_TOKEN = '<token>'
& "$case\Scripts\fetch_svd.ps1"                    # API 直连 + S3 走代理
& $bl --background --factory-startup --python "$case\Scripts\inspect_svd.py"          -- $case
& $bl --background --factory-startup --python "$case\Scripts\analyze_body_islands.py" -- $case
& $bl --background --factory-startup --python "$case\Scripts\list_lower_shells.py"    -- $case
& $bl --background --factory-startup --python "$case\Scripts\color_shells.py"         -- $case 24
& $bl --background --factory-startup --python "$case\Scripts\separate_svd_parts.py"   -- $case
python "$case\Scripts\prepare_textures.py" $case
& "$case\Scripts\run_headless.ps1" -Script "$case/Scripts/import_svd.py"  -LogName 'import-svd.log'
& "$case\Scripts\run_headless.ps1" -Script "$case/Scripts/verify_svd.py"  -LogName 'verify-svd.log'
# 目标结构侦察（只读）
& "$case\Scripts\run_headless.ps1" -Script "$case/Scripts/recon_weapons.py"   -LogName 'recon.log'
& "$case\Scripts\run_headless.ps1" -Script "$case/Scripts/recon_skeletons.py" -LogName 'recon-skel.log'
```

## 注意事项

1. **Blender 5.1 没有 Collada 导入插件**，作者原包网格是 `model.dae`；几何改用 Sketchfab 的 glb，贴图仍用原包 4096² 原图。
2. **源法线全平滑**（0 个 >25° 锐边），硬边由 4096 法线贴图承担。
3. **UE 5.8 Python 读不到骨骼名**（`BoneNode.name` protected、`reference_pose` 返回 AnimPose）；目标骨骼清单从 M4 源 FBX 读出（100 根，含 `WPN_*` 挂点）。
4. **源里没有独立枪机**，`WPN_bolt` 与抛壳口需要后续再分或另建。

## 网络（本轮实测）

`api.sketchfab.com` 直连、`*.s3.amazonaws.com` 走代理 `127.0.0.1:7897`：源包 37.9 MB / 3.7 秒、glb 6.1 MB / 2.6 秒。预签名链接 300 秒过期，中断重试会 403。
