# SVD 模型、分件与材质导入（2026-09-22）

> 本文保留该阶段的制作与检查记录。当前认可的换弹手型、最新材质／接口及归档恢复边界，以 [SVD 发布说明](svd-publication-20260923.md) 为准；旧版本的导入成功不代表最终手型获认可。

> **2026-09-23 当前状态更新：** 本枪已完成专用源资产和运行接入，当前目录为 `Complete20260923`，详见 [SVD 开发补齐](svd-completion-20260923.md)。下文是前期导入历史；其中“未接入”“复用 M4 动作”、旧挂点/侧倾测量和当时待办均不是当前标准。源坐标与动画空间混用的测量已重做。

用户指定模型：<https://sketchfab.com/3d-models/svd-dragunov-sniper-rifle-2ac78fb5a0eb40f5a02a5b0a9f566abf>（作者 **LeroyCake**，**CC BY 4.0**）。

按 [武器标准工作流](../../skills/ue5-weapon-workflow/SKILL.md) 执行主线推进：**① 许可与源审查 → ② 现有武器侦察 → ⑤ 机械分件（枪体 4 件 + PSO-1 瞄具 3 件）→ 导入为资产**。绑共享手臂、骨骼、动作、数值/图标/音效仍未做。

案例目录：[`SourceAssets/SVDDragunov20260922`](../../SourceAssets/SVDDragunov20260922/README.md) ｜ 来源散列：[PROVENANCE.md](../../SourceAssets/SVDDragunov20260922/PROVENANCE.md) ｜ 署名：[ThirdPartyNotices/SVD_DRAGUNOV.md](../../ThirdPartyNotices/SVD_DRAGUNOV.md)

## 1. 授权

**CC BY 4.0**：允许商用，**必须署名**。已登记第三方声明。

## 2. 执行主线第 2 步：现有武器侦察（目标结构）

从 M4 视图模型的源 FBX 读出骨架 **100 根骨骼**，其中武器挂点即新枪必须对齐的目标：

```text
WPN_root            枪体主根（整枪由它驱动）
WPN_SOCKET_Magazine 弹匣挂点          WPN_Trigger          扳机
WPN_bolt             枪机              WPN_ChargingHandle   拉机柄
WPN_BoltCatch        枪机释放           WPN_SOCKET_Muzzle    枪口（VFX）
WPN_SOCKET_Eject     抛壳口（VFX）      WPN_RearSight / WPN_FrontSight  前后瞄具
interaction / center_of_mass
```

手臂侧为项目默认 Manny 骨架（`root/pelvis/spine…`、`hand_l/r` 与五指、`ik_hand_gun`、`ik_hand_l/r`）。UE 5.8 的 Python **不暴露**骨骼名（`BoneNode.name` 是 protected、`reference_pose` 返回不可迭代的 AnimPose），因此骨骼清单从源 FBX 读。

## 3. 执行主线第 5 步：机械分件（枪体 + 瞄具）

源模型是 **758 个壳体的枪体 + 228 个壳体的瞄具**，机械件全部混在一起。分件做法是**按测量区域重组既有壳体，不裁切任何表面**（每个部件保持闭合、UV 与法线不变）：

| 部件 | 判定区域（源坐标） | 壳体数 | 三角面 | 对应目标挂点 |
| --- | --- | --- | --- | --- |
| `SM_SVD_Body` | 其余全部 | — | 19,252 | `WPN_root` |
| `SM_SVD_Magazine` | y∈[−0.270,−0.130]、z≤0.125、x∈[0.140,0.190] | 53 | 4,936 | `WPN_SOCKET_Magazine` |
| `SM_SVD_Trigger` | y∈[−0.300,−0.255]、z∈[0.055,0.100] | 17 | 428 | `WPN_Trigger` |
| `SM_SVD_ChargingHandle` | 凸出到 x≥0.198（机匣右侧） | 5 | 96 | `WPN_ChargingHandle` |
| `SM_SVD_SafetyLever` | x≥0.185、z∈[0.125,0.160]、x 向薄 | 20 | 728 | （骨架无对应骨骼，独立件保留） |
| `SM_SVD_ScopeBody` | 其余全部 | — | 3,859 | 瞄具挂点（待标定） |
| `SM_SVD_ScopeMount` | x≤0.156 且 z≤0.23（镜筒轴线 z≈0.259 的左下方） | 97 | 1,835 | 镜座（可换装） |
| `SM_SVD_ScopeLens` | 沿 Y 零厚度、圆形（长短径差≤6 mm）、居中于镜筒轴线 | 11 | 355 | — |

**合计 31,489 面，与源 glb 完全一致**（无几何丢失或重复）。区域不是猜的：`color_shells.py`/`analyze_scope_shells.py` 给最大壳体上色渲染定位，`list_lower_shells.py` 列出所有"挂在机匣下方／右侧凸出"的壳体定量确认，`separate_svd_parts.py` 分件后出彩色验证图（`Previews/mechanical/`）。

瞄具三件的含义：**镜筒**（管身、目镜罩、物镜端、高低／风偏转螺、照明座）、**镜座**（扣在机匣导轨上的侧装卡箍，与镜筒分开以便装拆与共用挂点）、**镜片组**（沿镜筒 11 片零厚度光学件，口径 2.9–5.7 cm，含物镜／转像镜／分划／目镜）。

**源里没有独立枪机（bolt）**：`WPN_bolt` 与抛壳口需要后续从枪体再分或另建。

## 4. 导入结果

内容根 `/Game/Weapons/SVDDragunov20260922`，**八个部件共用同一坐标原点**（摆同一变换即为整枪装配，绑骨骼时也共享同一坐标架）：

| 网格 | 三角面 | 尺寸 (cm) | 材质实例 | 贴图组 |
| --- | --- | --- | --- | --- |
| `SM_SVD_Body` | 19,252 | 3.73 × **122.5** × 17.80 | `MI_SVD_Body` | `svd_*` |
| `SM_SVD_Magazine` | 4,936 | 2.67 × 10.07 × 10.03 | `MI_SVD_Magazine` | `svd_*` |
| `SM_SVD_Trigger` | 428 | 1.78 × 1.87 × 3.13 | `MI_SVD_Trigger` | `svd_*` |
| `SM_SVD_ChargingHandle` | 96 | 2.21 × 2.01 × 0.63 | `MI_SVD_ChargingHandle` | `svd_*` |
| `SM_SVD_SafetyLever` | 728 | 0.61 × 10.88 × 3.54 | `MI_SVD_SafetyLever` | `svd_*` |
| `SM_SVD_ScopeBody` | 3,859 | 7.64 × 30.69 × 13.74 | `MI_SVD_ScopeBody` | `pso_*` |
| `SM_SVD_ScopeMount` | 1,835 | 3.04 × 15.29 × 7.69 | `MI_SVD_ScopeMount` | `pso_*` |
| `SM_SVD_ScopeLens` | 355 | 4.05 × 30.05 × 4.05 | `MI_SVD_ScopeLens` | `pso_*` |

- 归一化：等比缩放到实枪全长 **1.225 m**（源 1.7208 单位，比例 0.711862），枪口 −Y / 上方 +Z（项目 FBX 约定 → UE 中 +X 正向）。
- 贴图 10 张 **4096²**（`svd_*` 与 `pso_*` 两套 albedo/normal/roughness/metallic/AO）；normal 无损 PNG 且翻转绿通道，其余 TC_DEFAULT / TC_MASKS。
- Nanite 关闭；实体件三角面碰撞，镜片组 `none`；材质参数化（`Tint` / `RoughnessScale`），数值在 MI 上。
- 回执 `Receipts/import.json`、`Receipts/parts.json`、`Receipts/verify.json`。

## 5. 本轮踩到的坑

1. **Blender 5.1 不再附带 Collada 导入插件**，作者原包网格是 `model.dae` → 几何改用 Sketchfab 的 glb（面数与页面申报相符），贴图仍用原包 4096² 原图。
2. **源法线全平滑**（0 个 >25° 锐边、最大夹角 0.05°），硬边由 4096 法线贴图承担——已确认源本身如此（`has_custom_normals=True`）。
3. **分件脚本第一版用面索引选择**，分离一次后 Blender 重建数组导致 `IndexError`；改为"按材质分组 + `separate(type='MATERIAL')`"。
4. **材质命名**：`str.capitalize()` 会把其余字母小写，生成了 `MI_SVD_Charginghandle`；改为在配置里显式给 `part_name`。
5. **不要在编辑器加载着资产时删磁盘 `.uasset`**：为清理上一轮的错误命名文件这么做之后，编辑器里的包变成脏包，随后导入被自己的守卫拦下（`Unsaved work in our own packages`）。正确做法是通过资产 API `EditorAssetLibrary.delete_asset` 退役（脚本已加入 `STALE_ASSETS` 步骤）。
6. **镜座判定要排除偏移方板**：仅用"沿 Y 零厚度"会误收镜座附近的一块方板（island 421），加"圆形（长短径差≤6 mm）且在镜筒轴线上"后修正（镜片组 12 片 → 11 片）。
7. **UE 资产路径不区分大小写**：按正确名 `M_SVD_ChargingHandle` 创建时命中了已存在的 `M_SVD_Charginghandle`，磁盘文件名不跟着变；只能用 `rename_asset` 先改临时名再改回。而且这次改名**把两个材质实例的父级引用弄成了 null**（`MI_SVD_ChargingHandle`/`MI_SVD_SafetyLever`），必须重设 `set_material_instance_parent` 并复验——是独立读回抓到的。
8. **槽名子串匹配会串位**：`'Body'` 是 `'ScopeBody'` 的子串，导致 `SM_SVD_ScopeBody` 槽被判给了 `MI_SVD_Body`；按部件名长度降序匹配后修正。
9. **骨骼网格的材质 API 与静态网格不同**：`SkeletalMesh` 没有 `get_material/set_material`，`SkeletalMeshEditorSubsystem`（5.8）也没有 `set_material`；正确做法是读 `materials` 数组、对每个 `SkeletalMaterial` 用 `set_editor_property('material_interface', ...)` 再整体写回。另 `FbxSkeletalMeshImportData` 没有 `combine_meshes`（那是静态网格属性）。

## 6. 绑手臂的准备工作（本轮完成，未接入）

按技能"先读现有宿主"，把 M4 视图模型与项目动画都读了一遍，得到两条关键结论：

**① 绑定姿势不是持枪姿势。** 把 M4 的 `SK_M4_FoldingSights_HK416.fbx` 导入后渲染，**M4 本身也浮在手臂上方**（手臂网格中心 z≈−0.42，武器在 z≈−0.02）：这个 FBX 的 rest pose 并非持枪姿态，不能拿它当握持判据。手臂/武器网格都挂在 `SK_M4_Infima` 骨架下、带 Armature 修改器，手的实际位置由动画决定。

**② 手相对 `WPN_root` 的位置由骨架+动画固定**，这才是新枪要对齐的参照。从项目现成的 `A_AKM_idle.fbx`（同一套 Manny 手臂与 `WPN_*` 骨骼）在动画中段采样，得到相对 `WPN_root` 的接触区：

| 部位 | 相对 WPN_root（米） | 含义 |
| --- | --- | --- |
| 右手腕 / 拇指 / 食指 | y −0.110 … +0.065，x +0.02 … +0.03 | **握把接触区**（手掌包握范围） |
| 左手腕 / 拇指 / 食指 | y +0.193 … +0.308，x −0.019 … +0.027 | **护木支撑区** |
| `WPN_SOCKET_Magazine` | y +0.143 | 弹匣挂点 |
| `WPN_SOCKET_Muzzle` | y +0.586 | 枪口挂点 |

**③ SVD 的放置**（`Scripts/align_to_arms.py`）：实测两枪的扳机都在握把**前方**（M4 +6.7 cm、SVD +8.5 cm）、弹匣也都在握把前方（M4 +14.8 cm、SVD +13.5 cm）——**两枪同向（枪口 +Y），不需要旋转**，因此只做平移，把 SVD 握把中心对齐到 M4 握把中心（相对 WPN_root 为 −0.018，落在动画手掌区间内）：

- 对齐结果：平移 `(0.0426, 0.4082, −0.0900)`、yaw 0°；**握把误差 0.0 mm**；
- 残余：扳机距 M4 扳机位 **3.7 cm**、枪膛线比 M4 低 4.0 cm——两枪的"握把→扳机"几何本就不同（M4 7.84 cm / 抬高 4.0 cm，SVD 8.55 cm / 抬高 0.8 cm），刚体变换无法同时满足；
- 中间踩的坑：第一版用"握把→扳机朝向"求 yaw，把近乎共线的向量的噪声放大成 3.7° 偏航，又叠加了一次 180° 旋转，结果扳机偏到 15.6 cm——**是渲染图与回执数字一起把它抓出来的**。

**结论**：握把已按动画手掌对齐，可作为绑定起点；**扳机指位、开镜眼距与托枪手位置必须在实际持枪姿势（绑定+动画）里做最终标定**，也就是技能里的四项量化检查。对齐后的装配另存 `Authored/SVD_Aligned.blend`。

## 7. 视图模型绑定（本轮完成）

按项目布局，一把枪的运行网格是**手臂 + 武器合一的骨骼网格**（M4 即 `SK_M4_FoldingSights_HK416`），所以 SVD 也做成同构：

| 项 | 值 |
| --- | --- |
| 资产 | `/Game/Weapons/SVDDragunov20260922/Viewmodel/SK_SVD_Manny`（10.89 MB） |
| 骨架 | **复用 `/Game/Weapons/M4HK416Replica/SK_M4_HK416_Skeleton`**（导入时 `options.skeleton = <M4 mesh>.skeleton`，不新建骨架） |
| 组成 | 共享 Manny 手臂（20,326 顶点）+ SVD 八件（25,195 顶点）；LOD0 **52,189 顶点**、10 个 section |
| 骨骼绑定 | 每件刚性绑定（单一顶点组、权重 1.0）：Body→`WPN_root`、Magazine→`WPN_SOCKET_Magazine`、Trigger→`WPN_Trigger`、ChargingHandle→`WPN_ChargingHandle`；SafetyLever 与瞄具三件→`WPN_root`（骨架无对应骨骼，光学专用骨留到瞄具系统接入时再加） |
| 材质槽 | 10 个全部映射：手臂两槽**直接复用 M4 当前材质** `MI_Manny_01/MI_Manny_02`（保住了已认可的手套外观），八件各用 `MI_SVD_*` |
| 尺寸校验 | 网格包围盒 `[110.87, 122.5, 77.47]` cm——**X 向 110.87 与 M4 完全相同**（同一副手臂），Y 向 122.5 即 SVD 全长，与 M4 的 71.59 对应同一约定 ✓ |

**这一步同时回答了先前挂着的朝向疑问**：UE 里 M4 的武器长度就在 **Y**（71.59 cm ≈ 实测 69 cm，X 的 110.87 是展开的手臂），QBZ 亦然——SVD 的 Y 向 122.5 cm 与项目武器约定一致，**不需要补 90° 旋转**。视图模型与静态网格两处读回的尺寸互相印证，也与 M4 自己的一致。

回执：`Receipts/rig.json`（Blender 侧）、`viewmodel_import.json`（导入）、`viewmodel_verify.json`（独立读回）。

## 8. 开镜与接触点标定（本轮完成测量，未接入代码）

按 `FPSGAMECharacter.cpp` 的 ADS 标定口径（约 2708 行）读数：`Rear/Front` 是**武器空间**的两个瞄点，相机被放在 **Rear 点前方 `EyeDistance`** 处（`CalibratedADSLocation = FVector(EyeDistance,0,0) − R·Rear`）。共享的 `WPN_RearSight/WPN_FrontSight` 骨位于 M4 的机械瞄具处，AKM 因此用自己的 `AKMSoviet::Rear/Front` 常量——SVD 同样需要自己的一对。

**测得（武器空间，厘米；+Y 为枪口，原点为整枪包围盒中心）**：

| 项 | 值 | 说明 |
| --- | --- | --- |
| PSO-1 光轴后端（目镜面） | `(1.86, −38.93, 9.42)` | 由镜片组 11 片圆盘量出 |
| PSO-1 光轴前端（物镜端） | `(1.86, −8.89, 9.42)` | 与后端同轴 |
| 建议 `ADSRearEyeDistance` | **7 cm** | PSO-1 实镜出瞳距离 68 mm（M4/QBZ 机瞄 12、ASH-12 中置照门 18） |
| 扳机指位残余 | **1.49 cm** | 动画食指指尖与 SVD 扳机中心之差（AKM idle 姿势实测） |
| 枪口相对共享挂点 | `(4.38, **70.25**, −7.59)`，距离 **70.79 cm** | 见下 |

**两个必须记录的结构性发现**：

1. **共享 `WPN_SOCKET_Muzzle` 是按 M4 长度放的**。对 0.69 m 的 M4 只需 4.84 cm 的枪口后偏，ASH-12 是 6.79 cm；而 1.225 m 的 SVD 真实枪口在这个挂点**前方 70.25 cm、下方 7.59 cm**。也就是说**枪口烟火/曳光不能直接复用 M4 的偏移量**，SVD 要么用这个大偏移常量，要么在后续给它自己的枪口挂点。
2. **扳机指位其实是对的**：先前算出的"扳机差 3.7 cm"是相对 **M4 扳机网格中心**；按真正动画食指指尖量，SVD 扳机中心只差 **1.49 cm**——说明"以握把对齐"的做法成立，不需要再整体挪枪。

测量结果已按项目"每枪一个参数头"的约定写成 [`Source/FPSGAME/Weapons/SVDWeaponAssets.h`](../../Source/FPSGAME/Weapons/SVDWeaponAssets.h)（含 `SightRear/SightFront`、`ADSRearEyeDistance`、`MuzzleFromSharedSocket`）。**该头文件目前没有被任何 cpp 包含，编译结果不变**——接入需要改 `FPSGAMECharacter.cpp` 的武器分支并做一次完整 Editor 构建。

## 9. 武器接入（代码 + 数据 + 图标，已写完，待编译）

### 9.1 代码

| 文件 | 改动 |
| --- | --- |
| `Source/FPSGAME/Weapons/SVDWeaponAssets.h` | 新增：路径、瞄点、出瞳距离、枪口偏移等实测常量（`Matches()` 按 `/Game/Weapons/SVDDragunov20260922/` 前缀判定） |
| `FPSGAMECharacter.h` | 新增 `bSingleShotTrigger`（默认 false）与 `UsesSingleShotTrigger()` |
| `FPSGAMECharacter.cpp` | ① include 头文件；② 武器分支：载入视图模型、`bUsingM4Infima=true`、半自动开关、`ADSRearEyeDistance`；③ ADS 标定新增 SVD 分支（用 `SightRear/SightFront`）；④ 三处触发路径改用 `UsesSingleShotTrigger()` |
| `FPSGAMECharacterProfile.cpp` | 武器白名单加入 `ue_svd` |

**半自动**：项目原本只有手枪是"一按一发"（`bPistolShotPending` 仅对手枪生效）。新增的开关只替换触发路径的四个判断点（`FirePressed` 置位、`ServiceHeldFire` 放行、连发补射循环 break、`FireShot` 消耗），**不碰 `IsPistolWeapon()`**，因此不影响手枪的构图、移动、双持等既有行为；默认 false，其他武器行为不变。

### 9.2 动画与音效：复用 M4（已量化复核）

`bUsingM4Infima=true` 使 `LoadAKMAnimation` 落到 M4 分支：待机/开火/开镜开火/检视取 `/Game/Weapons/M4ContactImpactFinal/`，换弹与装备取 `M4TacticalTossFinal` / `M4SlapImpactFinal` / `M4WrapGripFinal`；`LoadAKMSound` 相应改用 HK416 套件。这要求网格绑在共享骨架上——SVD 正是如此。

技能要求"复用现成动作必须重新测量接触"，因此量了弹匣与共享挂点的关系：

| | 弹匣中心相对 `WPN_SOCKET_Magazine` |
| --- | --- |
| M4 | (−0.32, +4.87, +4.62) cm |
| SVD | (−0.33, +3.64, +3.41) cm |
| **差** | **(−0.01, −1.23, −1.21) cm** |

即换弹动画里手与弹匣的接触点偏差约 **1.2 cm**，可以直接复用。另测得 **PSO-1 光轴比共享机瞄骨低 4.8 cm**（`WPN_RearSight` z≈14.24、镜轴 z≈9.42），这正是第 8 节要给 SVD 单独一对瞄点的原因。

### 9.3 数据注册

| 文件 | 内容 |
| --- | --- |
| `items.json` | `ue_svd` 条目：武器类、双手、图标 `Icons/ue_svd.png`、物理攻击 65、弹匣容量 10 |
| `gunsmith.json` | `ue_svd`：`allowed: []`（暂无配件网格）、`ammo_item_id` = **`ammo_pkm_762x54r`（7.62×54R LPS，项目已有）**、弹匣 10、伤害 65、射击间隔 0.35 s、换弹 3.6 / 空仓 4.6 s、弹速 520、有效射程 150、后坐 120、散布 1.6 |
| `combat-weapon-formulas.json` | `ue_svd`：`base` 15、`enhanceFlat` 1.05、int/wis 各 0.48（每强化 0.085） |
| `Content/ColdSteelData/Icons/ue_svd.png` + `ue_svd.uasset` | 768×320 透明底朝左图标，纹理设置与已认可的 `ue_m4a1` 图标一致（sRGB、TC_DEFAULT、TEXTGROUP_WORLD） |

数值口径参照现有条目（M4A1 24、A762 33.25、ASH-12 48 伤害；PKM 有效射程 150），属**平衡取值而非实测**。弹速同理：项目内 7.62×39 记 350、12.7mm 记 300，不是真实 m/s，所以 SVD 取 520 作为精确步枪的相对值。

### 9.4 编译与接线解析（已完成）

`Tools/Build/Build-Editor.ps1` 编译 **127/127 通过**（68.6 秒，`Result: Succeeded`，日志 `Saved/BuildEditor/build-20260923-000847.log`；仅其他文件既有警告）。构建脚本要求先关闭 FPSGAME 编辑器，期间未强制结束任何人进程。

编译后用 `Scripts/verify_asset_resolution.py` 按代码的真实解析路径逐项载入，结果 **`ok: true`、无缺失**：

| 类别 | 解析到的资产 |
| --- | --- |
| 姿势剪辑 | `M4ContactImpactFinal/A_AKM_{idle,aim,fire,aim_fire}`（3.000 / 0.033 / 0.767 / 0.767 秒） |
| 换弹装备 | `M4TacticalTossFinal/A_M4_HK416_reload` 2.100 s、`M4SlapImpactFinal/A_M4_HK416_reload_empty` 2.700 s、`M4WrapGripFinal/A_M4_HK416_equip_charge` 0.633 s |
| 机械音效 | `M4HK416Audio/S_HK416_{Fire,MagOut,MagInsert,MagSeat}`、`M4AnimationAuditFinal/S_HK416_Equip` |
| 资产 | 视图模型 `SK_SVD_Manny`、图标 `Icons/ue_svd` |

检查过程中澄清了一处**看起来像错误其实不是**的现象：idle／开火剪辑在 `SK_M4_Infima_Skeleton` 上，而视图模型在 `SK_M4_HK416_Skeleton` 上。两个骨架不同，但前者在后者声明的 `compatible_skeletons` 列表里（101 根对 99 根骨，UE 官方的同构骨架共享动画机制），因此**合法可用**；M4A1 本身走的也是同一条路径。检查脚本已按"相等或声明兼容"的口径修正，避免下次误报。

未解析的只有 `A_AKM_inspect`（M4 姿势时钟下 `InspectAnimation` 本就置空）与 `A_AKM_equip_charge_empty`（仅空仓装备时解析，M4A1 同样取不到，属项目既有状态），二者都不是 SVD 引入的缺口。

## 11. 实机反馈的两个问题与处理（2026-09-23）

用户实测反馈：**① 第一人称手里的枪是灰白/棋盘格；② ADS 时枪身侧倾。**

### 11.1 没贴图：材质缺 SkeletalMesh 用途标记（已修，日志铁证）

游戏日志直接给出根因：

```text
LogMaterial: Warning: Material .../MI_SVD_Body missing usage flag SkeletalMesh!
             Default Material will be used in game.
LogSkeletalMesh: Warning: Material with missing usage flag was applied to skeletal mesh
                 /Game/Weapons/SVDDragunov20260922/Viewmodel/SK_SVD_Manny
```

八个 `MI_SVD_*` 全部中招——材质是用 Python `MaterialFactoryNew()` 建的，**从未勾选 "Used with Skeletal Mesh"**，UE 因此拒绝全部 shader 变体、回退默认材质（WorldGrid 棋盘格）。**资产槽位绑定一直是正确的**（十槽都指向 MI，实例父级与贴图覆盖齐全，UV 完好 12,788 个坐标），所以此前所有资产级检查都是绿的——这类问题只有运行时日志能暴露。

修法（`Scripts/fix_material_usage_flags.py`）：从 M4 现用材质 `M4InfimaV3/MI_Manny_01` 抄用途标记（实测它只开了 `used_with_skeletal_mesh` 一项），逐个设置、重编译、保存，再复验八个实例经父级都报告该标记。**结果 `all_ok: true`。**

教训：**Python 新建的材质必须显式打开用途标记**，否则静态网格能显示、骨骼网格回退默认材质。此坑不写进日志以外的地方看不见，建议后续新建枪械材质一律沿用"抄参考材质的用途标记"这一步。

### 11.2 ADS 侧倾：三种口径互相矛盾，按最可靠口径**撤回**修正

按技能第 52 行（ASH-12 案例）的方法量滚转，得到互相矛盾的三个数：

| 口径 | M4 | SVD | 差 |
| --- | --- | --- | --- |
| 顶面**面积加权**法线 | −3.688° | −0.648° | **3.04°** |
| 最高处**窄带**法线 | +8.130° | **0.000°** | 不适用 |
| **主轴分析（PCA）** | −0.572° | +0.085° | **0.658°** |

- 面积加权口径不可信：SVD 的朝上面积 0.121 m² 是 M4（0.028 m²）的 4 倍，斜木护木与贴腮板把均值带偏；
- SVD 的**平坦顶面实测恰好 0.000°**（水平），窄带口径对 M4 又被导轨齿与准星污染；
- **PCA 与形状无关**，最可信：SVD 与 M4 只差 **0.658°**，还小于 M4 自身 aim/idle 的散布（−0.03/+0.37）。

因此**已把先前按 3.04° 做的反向滚转撤回**（`Receipts/roll_vs_m4.json` 的 `applied_angle_deg = 0.0` 并记录理由）：按被污染的口径去修正，等于把它本来没有的倾角拧进去。装配脚本读该字段，日后有视觉确认再启用。

同时用日志里的运行时标定读数复核了 ADS 轴向，**标定本身正确**：

```text
GUNPLAY_ADS_CALIBRATED rear=V(X=-1.86, Y=29.31, Z=-0.44) front=V(X=-1.86, Y=-0.73, Z=-0.44)
                       offset=V(X=36.31, Y=1.86, Z=0.44) rotation=R(Y=90.00, R=0.00)
```

轴向长 30.04 cm（＝目镜 38.93 与物镜 8.89 之差）、方向 −Y（组件空间的枪口方向），旋转只有基准的 90° 偏航、无额外偏转，`offset.X = EyeDistance(7) + 后点 Y(29.31) = 36.31` 与公式完全吻合。

### 11.3 顺带修掉的半自动粘滞

`bSingleShotTrigger` 原先只在 SVD 分支里赋值，切到别的枪不会复位，会让之后所有步枪都变半自动。已改为在 `InitializeWeaponVisuals` 开头统一复位。已重新编译（127/127 Succeeded）。

## 12. 还没做的部分（武器接入剩余）

1. **绑定共享手臂**：复用 `SK_Manny_Arms_Export`（运行外观以 `/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416` 为准），把八个部件按上表挂到 `WPN_*` 骨骼，适配握持与袖口。
2. **枪机与抛壳口**：`WPN_bolt` 需从枪体再分或另建；`WPN_SOCKET_Muzzle` / `WPN_SOCKET_Eject` 按实测标定。
3. **镜片材质**：镜片组目前沿用 `pso_*` 扫描材质；项目光学玻璃／分划材质规范另属一步。
4. **动作**：待机／开火／换弹（普通与空仓）／拉栓／装备／冲刺／快速近战，含音效与补弹的时间映射。
5. **数值与索引**：`gunsmith.json` 条目、物品注册、拾取、图标、7.62×54R 弹药与弹匣容量、强化系数。
6. **音效**：开火／换弹／拉栓。
7. **四项量化检查**（绑手臂后）：枪身滚转（M4 基准 aim −0.03° / idle +0.37°）、开镜眼距（PSO-1 侧装镜，不能照抄 M4 的 12 cm）、共享瞄具鞍座落差、硬边完好（本例源为全平滑，判据按此源调整）。
8. **实机验收**：未做游戏运行、PIE、截图与性能验收。

## 8. 待办：材质重建排队中

上一轮为修正材质命名（`MI_SVD_Charginghandle` 这类 `str.capitalize()` 的产物）**在编辑器加载着资产时删了磁盘 `.uasset`**，导致编辑器内的包变脏、随后的导入被自己的守卫拦下。当前 `Materials/` 是半成品（Body/Magazine/Trigger 正常，ChargingHandle/SafetyLever 只有错名母材质、瞄具三件材质缺失）。

- 修复方式：干净重建的离线导入已排队（`Scripts/import_svd.py` 增加了通过资产 API `delete_asset` 退役陈旧命名的步骤），**等占用编辑器的会话释放后自动执行**；
- 未结束他人编辑器、未发送跨会话协调消息，符合项目规则；
- 网格侧 8 件已全部在盘上，材质重建不影响几何。

## 7. 边界

- 只导入资产，**关卡里没有任何摆放**，武器系统未接入，**还不是可用的枪**。
- 材质是源材质直出，未按"枪身材质统一"标准做分区涂层。
- 源为塑料枪托版本；镜座与镜筒已分开，后续可做装拆与共用挂点。
