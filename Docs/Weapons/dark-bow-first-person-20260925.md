# 暗纹猎弓：第一人称接入记录（2026-09-25）

对应需求：把 Fab 导入的 **dark bow** 引入第一人称，并参考 **Paragon Sparrow** 的待机与拉弓动作，
设置一把可用的弓类武器。本轮全部在后台完成（代码、数据表、headless 导入与实测），
**未启动编辑器、未进 PIE、未做手感与视觉验收**。

---

## 1. 资源来源与许可（逐条）

| 资源 | 来源 | 许可与使用边界 |
| --- | --- | --- |
| `Content/Weapons/DarkBow20260925/SK_DarkBow` + `Material_002/003/005` | Fab 组合包 **"dark bow"**，卖家 **M@xim**，uid `87a3b4bc-423e-459e-beb6-c9bc59470d9c`，2026-03-11 发布，提供 fbx / gltf-usdz / blender 三种格式；本地缓存 `VaultCache/FabLibrary/dark_bow-87a3b4bc/fbx/`（卖家信息记自本轮之前的 Fab 库条目读取，本轮未重新联网核对） | Fab EULA：仅授权在本项目内使用，**不允许再分发原始资源**。因此 `SourceAssets/DarkBow20260925/Source/dark_bow.fbx` 与 `Content/Weapons/DarkBow20260925/*.uasset` 属于未审核再分发许可的二进制，**不做公开提交**；提交前按 AGENTS.md 的资产边界处理 |
| Paragon **Sparrow**（`Content/ParagonSparrow/...`） | Epic 第一方 FAB 包 | 仅限 UE 生态使用。本轮**只读取片段时长做节奏参考**，没有把 Sparrow 的动画／骨架复制进弓的运行时路径 |
| 弓弦、箭杆、箭头 | 引擎基础图元 `BasicShapes/Cylinder`、`BasicShapes/Cone` | 程序化占位，见 §5；正式箭模通过 `bows.json` 换路径，不改代码 |

## 2. 实测数据（headless，非作者估值）

`SourceAssets/DarkBow20260925/ue_parts_readback.json`、`ue_import_readback.json`：

| 项 | 实测值 |
| --- | --- |
| FBX 原始包络（`import_uniform_scale=1`） | 113.057 × 10.385 × **414.087** cm，5710 三角，10243 顶点，3 个 section，单一网格节点 |
| 归一后 `SK_DarkBow` | **38.223 × 3.511 × 139.999** cm（导入缩放 `0.33809 = 140 / 414.087`），5710 三角，3 section，自动碰撞，无 Nanite |
| 包围盒中心（网格局部） | `(-6.574, -0.935, 0.153)` |
| 材质槽 | `Material_003` / `Material_005` / `Material_002`，都是 `MaterialInstanceConstant`，父材质 `/InterchangeAssets/Materials/FBXLegacyPhongSurfaceMaterial`（对应卖家说的"三块略有差异的黑色材质"） |

Sparrow 参考片段时长（`ue_readback.json`，骨架 `Sparrow_Skeleton`）：

| 片段 | 实测秒 | 用途 |
| --- | --- | --- |
| `idle` | **10.0** | 待机节奏参考（弓的 `ClipIdle` 循环基准） |
| `idle_relaxed` | 33.7333 | 未采用 |
| `Travel_Mode_Idle_BowDown` | 9.1667 | 未采用（收弓态） |
| `RMB_Drawback` | **2.4667** | 拉弓参考：整段含到位后的保持与回落 |
| `R_Ability_Slow_Fire` / `Med_Fire` | 1.0 / 1.0 | 释放节奏上界 |
| `R_Ability_Fast_Fire` | **0.6** | 释放 + 回收窗口锚点（作者取 0.30 + 0.34 = 0.64） |

骨架事实：`SK_Axe_BareArmsV7` → `SK_Harvest_Axe_Skeleton`，`SK_M4_BareArmsV7` → `SK_M4_HK416_Skeleton`，
`Sparrow` → `Sparrow_Skeleton`。**每个已认可的 V7 裸手 profile 用自己的原生骨架**，
所以弓不能直接借用斧／M4 的手臂，必须新做一套 Bow profile（§8）。

## 3. 节奏：哪些是实测，哪些是作者取值

`bows.json` 里同时留下两组键，避免把作者值当实测传播：

- 实测锚点（只读不改代码）：`reference_draw_clip_seconds = 2.4667`、`reference_fast_fire_clip_seconds = 0.6`、`reference_idle_clip_seconds = 10.0`。
- 作者取值（在实测区间内）：`nock_seconds 0.42`、`draw_seconds 1.4`、`hold_seconds 2.2`、`release_seconds 0.30`、`recover_seconds 0.34`。
  - `draw_seconds` 取 1.4 s：短于 `RMB_Drawback` 全长（含保持与回落），长于 Fast_Fire；
  - 释放 + 回收 = 0.64 s ≈ `R_Ability_Fast_Fire` 0.6 s；
  - 真正的接触帧（弦到颊侧、撒放瞬间）要等 Bow 裸手 profile 有动画后按逐帧复核再收口。

## 4. 坐标契约（实测推翻了我最初的假设）

导入包络说明这把弓：**长度沿局部 Z（±70）**、**前后沿局部 X**、**薄沿局部 Y（3.5 cm）**。
X 的两个极值是 `-25.69`（弓背最深）与 `+12.54`；网格自身原点（作者放在握把）到 `+12.54` 的距离
就是**实测弓档 ≈ 12.5 cm**，因此判定 **弦在局部 +X 侧**、弓背凸向 -X，箭朝局部 **-X** 出膛、拉弦往 +X 退到颊侧。
要让出膛方向对上相机 +X（准星），挂载基准偏航 **180°**，故 `bow_rotation_deg = "0,180,-6"`。

这条判定来自包络 + 官方缩略图（弓竖直、深反曲、弦为一条直线）的交叉推断，**属于未实测**：
实机若看到弦在远离准星的一侧，把 `bow_rotation_deg` 的偏航改成 `0`（并把 `nock_*/brace_nock/draw_anchor` 的 X 反号）即可，
不需要改代码。`fps.Bow.LocationOffset` / `fps.Bow.RotationOffset` / `fps.Bow.Sway` 是实机对点用的叠加 cvar，默认 0／1。

## 5. 运行时结构

新增 `UBowWeaponComponent`（`Source/FPSGAME/Weapons/Bow/`），与 `UProductionToolComponent` 同族：
相机空间挂点、单一动作时钟、物品 Data 驱动资源路径，**不引入 AnimBP／蒙太奇资产**。
弓体本身不直接挂网格，而是一张按槽名寻址的**部件表**（弓体／弓弦／弦上箭三件，见 §7）。

- 阶段机：`Stowed → Equip → Ready ⇄ (Nocking → Drawing → Holding → Release → Recover)`。
  满拉后 `hold_seconds` 到点自动撒放；右键 `steady` 把呼吸抖动压到 `steady_sway_scale`。
- 输入契约（`FPSGAMECharacter.cpp`）：左键按下＝搭箭（扣 1 支）并持续拉开，**只有真实松开才发射**，
  中途被打断走 `CancelAction()` 不放箭；右键＝稳持；R＝手动重新搭箭；滚轮／G 换武器沿用既有轮换。
  弓**不**进 `FPSGAMECharacterProfile.cpp:43` 的枪械 definition 白名单，所以枪械视模保持隐藏、弓自己出画。
- 弓弦与箭是**程序化几何**：两根细段把上下弓梢连到"弦结点"。弦结点优先取手臂 `hand_r` 骨骼的世界变换
  （反算到弓局部），没有裸手视模时在 `brace_nock_cm → draw_anchor_cm` 之间按拉距插值。
  本包的弦是**烘进网格的直线**：静止位程序化弦与它重合（看不出差），拉开后会双线。
  消法已留好数据口——`bow_part_string_material` + `bow_part_string_hide_slot`，两个键都填才生效，
  且用**组件级材质覆盖**（落在 `riser` 部件上），不修改资产本身（第三人称／掉落物不受影响）。
- 箭走既有**弹药袋**语义：`arrow_wood` / `arrow_broadhead` 已加进 `ammo_types.json`（18 → 20 行），
  `PouchCount / SpendAmmo / GrantAmmo` 直接复用；开发面板"无限备弹"按弹种生效（`allow_infinite_reserve`）。
- 弹道 `ABowArrow`：分步推进（单步 ≤ 60 cm）+ 球形扫掠，重力积分，箭身跟随速度方向；
  命中按 `ColdSteelSkills::ApplyHit` 唯一入口结算一次，再 `NotifyConfirmedWeaponHit` 出反馈，与枪械／法球同口径；
  命中后插住 8 s 再消失，随被击组件（骨骼）移动。
- 屏幕下方复用 `UColdSteelPickupPrompt` 显示状态行：`弓名 · 拉距 % · 弦上 · 箭袋 · 阶段`。

## 6. 数据表字段契约

`Content/ColdSteelData/bows.json`（`category: "weapon_bow"` + `weaponType: "bow"`，
`ColdSteelInventory::IsBow` 判定；`equipSlot: "weapon"` + `isTwoHanded` 走既有双手武器规则，
`ColdSteelInventoryRules::CanEquip` 的主手槽 6／9 可装）。读取点全在
`UBowWeaponComponent::ApplyNumbers` / `RefreshEquipment`，代码里不留第二套数：

- 部件：`bow_part_slots`（逗号分隔的槽名清单）+ 每槽 `bow_part_<槽名>_mesh` / `_material` /
  `_hide_slot` / `_rods` / `_radius_cm` / `_scale`，详见 §7。
- 其余资源：`bow_viewmodel`、`bow_animation_prefix`（`Idle/Draw/Hold/Release/Nock` 五段角色名）、
  `arrow_head_mesh`（飞行中箭的箭头，箭杆走 `arrow_rest` 部件）、
  `bow_draw_sound`、`bow_release_sound`、`bow_nock_sound`、`arrow_ammo`。
- 节奏：`nock_seconds` `draw_seconds` `hold_seconds` `release_seconds` `recover_seconds`（+ 三个 `reference_*` 记录实测）。
- 数值：`full_damage` `min_damage_ratio` `full_speed_cm` `min_speed_ratio` `arrow_gravity_cm` `range_cm`
  `stamina_cost`；`critical_chance`（-1＝不覆盖修炼快照）与 `toughness_multiplier`（0＝不覆盖）只在配值时生效。
- 几何：`bow_length_cm` `bow_depth_cm` `arrow_length_cm` `sway_amplitude_cm` `steady_sway_scale`，
  以及 `"x,y,z"` 字符串的 `nock_upper_cm` `nock_lower_cm`（归 `riser`）
  `brace_nock_cm` `draw_anchor_cm`（归 `string`）`arrow_rest_cm`（归 `arrow_rest`）
  `bow_location_cm` `bow_rotation_deg` `bow_grip_trim_cm`（归 `riser` 挂点）`bow_arms_rotation_deg`。

发放链：`Source/FPSGAME/UI/ColdSteelBows.cpp` 的 `LoadBowDefinitions()`（在
`ColdSteelProfileRuntime.cpp:103` 与工具表同一处合并）+ `GrantBow()`（按 definition 幂等发放，
并把 24 支 `arrow_wood` 送进箭袋）；`ActiveBow()` 从已装备武器里按 `IsBow` 过滤。

**开发期自动发放**：`UBowWeaponComponent::BeginPlay` 会调一次 `GrantBow()`，所以进游戏就能用滚轮／G
换到弓，不需要编辑器操作。幂等按 definition 判定——存档里已有这把弓就不再重复给；但箭袋空了会在
下次进游戏时再补 24 支（开发便利，正式经济接入时把这次调用挪走或加版本闸门）。多把弓时
`GrantBow()` 只给目录里遍历到的第一把。

## 7. 部件拆分：弓体与弓弦各自独立（改造系统接入口）

新增 `UBowPartComponent`（`Source/FPSGAME/Weapons/Bow/BowPartComponent.{h,cpp}`）：
一个部件＝**一个挂点 + 一个网格来源 + 若干条程序化细杆**。弓组件不再直接持有网格子件，
而是持有一张按槽名寻址的部件表：

| 槽名 | 内容 | 细杆 | 说明 |
| --- | --- | --- | --- |
| `riser` | `SK_DarkBow` 实体网格 | 0 | 它的局部空间就是全部锚点的参考空间；`bow_location_cm`／`bow_rotation_deg`／`bow_grip_trim_cm`／`bow_part_riser_scale` 都落在它身上 |
| `string` | 空＝程序化两段 | 2 | 上／下弓梢 → 弦结点；给 `_mesh` 就换成真正的弦模型（此时把 `_rods` 设 0） |
| `arrow_rest` | 空＝程序化一段 | 1 | 弦结点到箭尖的弦上箭；`_mesh` 同时决定飞行中 `ABowArrow` 的箭杆网格 |

**一个槽只有一个网格来源**：`_rods == 0` 时网格挂在实体子件上，`_rods > 0` 时同一网格是细杆素材，
为空才回落引擎圆柱占位。因此不会出现"弦有两个网格来源"的第二套口径。

数据键统一为 `bow_part_<槽名>_{mesh,material,hide_slot,rods,radius_cm,scale}`，
槽清单来自 `bow_part_slots`（逗号分隔）。旧平铺键 `bow_mesh`／`arrow_mesh`／`string_radius_cm`／
`bow_string_hidden_material`／`bow_string_material_slot` 仍作为**回落**读，便于别的弓沿用旧写法；
`bows.json` 本身已全部改用部件键。

改造系统要接的只有三样：

1. 查询：`PartSlots()` / `FindPart(槽名)` / `PartMeshPath(槽名)`（都是 `BlueprintPure`，UI 直接可用）；
2. 写入：改这件物品 Data 里的 `bow_part_<槽名>_mesh`（以及数值键，如 `bow_part_riser_scale`）；
3. 刷新：调一次 `RefreshEquipment(Profile)`。

刷新走**表现签名**判断：`PresentationSignature()` 只看资源路径集合。签名没变（纯数值或参数改动）
就只重算 `ApplyNumbers` + `ApplyParts`，**不重载资产、手上不闪帧**；签名变了才重新异步加载并重新装配部件。
数据表新增槽时组件就地补建（挂在 `riser` 下），不必重建武器组件。

材质覆盖也在部件上：`SetMaterialOverride(hide_slot, material)` 用**组件级**覆盖，
不动资产本身——这正是消掉本包烘焙弦那条直线的手段（`bow_part_string_material` +
`bow_part_string_hide_slot`，槽名待编辑器确认，见 §9）。

## 8. 本轮改动文件

新增：`Source/FPSGAME/Weapons/Bow/BowWeaponComponent.{h,cpp}`、`BowPartComponent.{h,cpp}`、
`BowArrow.{h,cpp}`、`Source/FPSGAME/UI/ColdSteelBows.cpp`、`Content/ColdSteelData/bows.json`、
`Tools/Bow/add_arrow_ammo_types.py`、`Tools/Bow/check_bow_consistency.py`、
`SourceAssets/DarkBow20260925/Scripts/{author_dark_bow_geometry,measure_dark_bow_mesh,diagnose_dark_bow_parts,import_dark_bow_scaled}.py`
+ `Scripts/run_headless.ps1`、本文与 `SourceAssets/DarkBow20260925/ue_*.json` 实测回执。

修改：`Content/ColdSteelData/ammo_types.json`（+2 箭种）、`UI/ColdSteelInventoryTypes.h`（`IsBow`）、
`UI/ColdSteelStatusModel.h`（`ActiveBow/GrantBow/LoadBowDefinitions`）、
`UI/ColdSteelProfileRuntime.cpp`（装载弓表）、`FPSGAMECharacter.{h,cpp}`（组件＋输入＋镜头叠加）、
`FPSGAMECharacterProfile.cpp`（换武器时刷新弓组件）。

`FPSGAME.Build.cs:28` 已有 `Content/ColdSteelData/...` 整目录登记，`bows.json` 自动随包，不需再加。

## 9. 剩余只能在编辑器里做的部分

1. **V7 裸手 Bow profile**：按 `skills/ue5-fps-arms-animation/references/accepted-bare-hands.md` 的母版流程，
   新建弓的原生骨架 + "弓＋裸臂"合体 SK，登记 `modular_outfits.json`；在此之前 `bow_viewmodel` 留空，
   画面是"悬空弓 + 程序化弦"（刻意不假造手）。
2. **参考 retarget**：把 Sparrow `idle` 与 `RMB_Drawback` 重定向到 Bow 骨架，按项目命名导出
   `<prefix>...Idle` / `...Draw` / `...Hold` / `...Release` / `...Nock` 五段 UAnimSequence，
   填 `bow_viewmodel` + `bow_animation_prefix` 即自动生效（组件已按手动采样口径播放，与采集工具一致）。
   接触帧复核后回写 `draw_seconds` 等节奏。
3. **烘焙弦的材质槽**：在视口里逐个隐藏 `Material_002/003/005` 确认哪一段是弦，做一个隐形材质，
   填 `bow_part_string_material` + `bow_part_string_hide_slot`（覆盖落在 `riser` 部件的对应槽上）。
4. **挂载目测**：§4 的 yaw／位置按实机微调（cvar 对点后回写 JSON）。
5. **正式箭模 + 图标 + 音效**：`bow_part_arrow_rest_mesh`（弦上与飞行中的箭共用）／`arrow_head_mesh`、
   `ue_icon`（PNG 直读口径）、三段音效。
6. **改造系统本体**：部件表与刷新链已经数据驱动，还缺的是"可选件目录 + 材料消耗 + 面板"那一层
   （照 `tool-gunsmith.json` / `melee-gunsmith.json` 的 columns 口径给弓做一份 `bow-gunsmith.json`）。
7. HUD 弹药读数目前是弓自带状态行；若要进 `ColdSteelAmmoReadout` 的弹匣位显示"箭数 + 拉距"，是一处小改。

## 10. 状态

- **源码编译：通过**。`Tools/Build/Build-Editor.ps1` → `Result: Succeeded`，
  `Binaries/Win64/UnrealEditor-FPSGAME.dll` 2026-09-25 11:31:08（部件拆分之后）。
  本轮修掉的 5.8 API 口径：`FString::CreateParseDelimiter` 与 `FParse::ParseVector` 已移除（改
  `ParseIntoArray` + 自写 `"x,y,z"` 解析）、`TAutoConsoleVariable` 不支持 `FVector`／`FRotator`（改字符串）、
  `USkeleton::GetRefSkeleton` 不再公开（改 `USkeletalMeshComponent::DoesSocketExist`）、
  `GetSkeletalMesh` → `GetSkeletalMeshAsset`、`FRotator::ClampAxis()` → `Clamp()`、
  `FHitResult::GetBoneName()` → `BoneName` 字段、`USceneComponent::bVisible` 已被成员遮蔽（参数改名）。
- **数据自检：通过**。`python Tools/Bow/check_bow_consistency.py` 校验 bows.json 的键与代码读取点、
  部件槽是否齐三件且每槽键完整、资产是否真在盘上、箭种是否登记在 ammo_types.json。
- 真实运行验收：**未做**（按项目规则由用户测试）。§4 的朝向判定、锚点数值、节奏手感均为
  实测包络 + 参考片段推导，**未实测未测试**；没有裸手视模，画面是悬空弓 + 程序化弦。
- 未提交：本轮只落盘，不 `git add`；Fab 原始 FBX 与导入 uasset 的提交边界按 AGENTS.md 资产规则处理。
