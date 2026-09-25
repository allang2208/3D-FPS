# 第一人称弓：部件表拆分与相机空间武器组件

从 2026-09-25「暗纹猎弓（Fab dark bow）第一人称接入」沉淀。案例正文与实测表在
`Docs/Weapons/dark-bow-first-person-20260925.md`；本篇只留可复用的结构与口径，弓的具体数值不当通用标准。

## 什么时候用这条路线

- 武器**不是枪**（没有弹匣／装弹／机瞄状态机），又要吃库存实例、改造件与镜头叠加：弓、采集工具、盾、法杖同一族。
- 判断依据：需要 AnimBP／蒙太奇的枪械动画合同（`pistols.md` / `melee.md`）用不上，而手上表现又必须由物品 Data 驱动。
  这时用**相机空间组件 + 手动动画采样**，全部工作可在后台完成（不需要开编辑器建蓝图）。

## 部件表结构（改造系统的接入口）

一个可替换部件 = `UBowPartComponent`：**一个挂点（它自己就是 `USceneComponent`）+ 一个网格来源 + N 条程序化细杆**。
实体网格与细杆都是它的子件，所以「弓的局部坐标」＝ `riser` 部件的坐标空间，换网格、换缩放都不会让锚点跑偏。

| 槽名 | 内容 | 细杆 | 归它管的键 |
| --- | --- | --- | --- |
| `riser` | 弓体实体网格 | 0 | `bow_location_cm` `bow_rotation_deg` `bow_grip_trim_cm` `bow_part_riser_scale`、`nock_upper_cm` `nock_lower_cm`（弓梢＝弦的端点，几何属于弓体） |
| `string` | 上／下弓梢→弦结点两段 | 2 | `brace_nock_cm` `draw_anchor_cm`、`bow_part_string_radius_cm` |
| `arrow_rest` | 弦结点到箭尖一段 | 1 | `arrow_rest_cm` `arrow_length_cm`、`bow_part_arrow_rest_radius_cm` |

**一个槽只允许一个网格来源**：`_rods == 0` 时网格挂在实体子件上；`_rods > 0` 时同一网格就是细杆素材；
为空才回落引擎圆柱占位。这条约束是拆分的全部意义——否则「烘焙进网格的弦」与「程序化的弦」会有两套真相，
拉开后必然双线。

- 弦上箭与飞行中的箭共用 `arrow_rest` 的网格：换箭台件时手上与空中的箭一起变，不需要第二处登记。
- 材质覆盖用**组件级** `SetMaterial(Index, Material)`（部件的 `SetMaterialOverride(槽名或序号, 材质)` 封装），
  不动资产本身，因此第三人称／掉落物不受影响。这是消掉「烘进网格的弦」的唯一正确手段。
- 数据表新增槽时组件**就地补建**（挂在 `riser` 下），不必重建武器组件——加瞄具／稳定器只加键。

## 数据键与刷新合同

```
bow_part_slots = "riser,string,arrow_rest"          # 逗号分隔，为空用默认三件
bow_part_<槽名>_{mesh, material, hide_slot, rods, radius_cm, scale}
```

- 部件键优先，旧平铺键（`bow_mesh` / `arrow_mesh` / `string_radius_cm` / `bow_string_hidden_material`）只作**回落**，
  便于别的武器沿用旧写法；同一张表里不要把两套都填成不同值。
- 换件的三步：`PartSlots()` / `FindPart(槽)` / `PartMeshPath(槽)` 查询 → 改这件物品 Data 的 `bow_part_<槽>_mesh` →
  `RefreshEquipment(Profile)`。三个查询都是 `BlueprintPure`，UI 直接可用。**不提供 `ReplacePart` 这类 C++ 变更 API**，
  避免第二处事实源。
- 刷新走**表现签名**：`PresentationSignature()` 只看资源路径集合（各槽 mesh/material + 视模 + 动画前缀 + 箭镞 + 旧平铺键）。
  签名没变＝纯数值/参数改动，只重算数值与部件，**不重载资产、手上不闪帧**；变了才异步重载并重装。
- 自检：`python Tools/Bow/check_bow_consistency.py`。它校验键集合与代码读取点一致、`"x,y,z"` 可解析、
  `/Game` 路径在 `Content/` 真的落盘、槽清单齐三件且每槽键完整、纯程序化槽不能既无 `_rods` 又无 `_mesh`、
  给了替换材质却没给 `hide_slot`、箭种是否登记在 `ammo_types.json`。口径与 `Tools/Weapons/check_attachment_consistency.py` 同源。

## 程序化几何与占位

- 占位用引擎 `/Engine/BasicShapes/Cylinder`（轴向 +Z、长 100、半径 50）：拉伸时**粗细由 `_radius_cm` 决定、长度由端点决定**，
  两个自由度分开，别把半径也按长度缩放。
- 给了正式网格时按其 `GetBounds()` 自取轴（`BoxExtent.X > BoxExtent.Z` → 轴 +X）与作者长度，**不再拉伸粗细**。
- 视模子件统一口径：`NoCollision` / 不影响导航 / 不投影 / `SetOnlyOwnerSee(true)` / 默认隐藏。
- 挂点组件必须**先注册父挂点再建子件**，否则子件注册时拿不到有效父变换。

## 参考动作的时钟口径（没有动画资产时）

参考包（如 Paragon Sparrow）只给**实测秒数**当节奏上界，不复制片段、不引用第三方骨架：

- 待机与拉弓的片段长度用 headless 读回记录成 `reference_*_clip_seconds`，`draw_seconds` 这类作者值必须落在实测区间内并在文档标明是作者选择。
- 播放合同：只 `PlayAnimation` 一次 → `SetPlayRate(0)` → 每帧 `SetPosition(秒)`（循环段 `Fmod`，单向段 `Clamp`）→
  `TickAnimation(0, false)` → `RefreshBoneTransforms()`。**每帧重新起播会让手臂停在片段开头**（与采集工具同一口径）。
- 阶段映射：待机循环用累计视觉时钟；拉弓用 `DrawFraction() * DrawSeconds` 采样（这才是「参考拉弓动作」的正确接法）；
  搭箭与释放按阶段时钟正向播。片段缺失时采样函数自己隐藏视模，不报错。
- 骨架必须自有的：裸手 V7 各 profile 用的是自己的原生骨架，弓也需要一把「弓＋裸臂」骨架；
  在那之前 `bow_viewmodel` / `bow_animation_prefix` 留空，画面就是悬空弓 + 程序化弦——**刻意不假造手**。

## UE 5.8 实测与导入要点

- **不要相信文件名里的尺寸**。FBX 常按作者单位导入（本案原始包 414 cm 高，不是标称的 148 cm）；
  先量包络再按最长轴归一，并把 `import_scale`、归一后 `size_cm`、`origin_cm`、材质槽写进 `ue_import_readback.json`。
- 静态网格的**长度轴不一定是 X**：本案长度沿局部 Z、弦在 +X 侧、薄沿 Y。锚点、出膛方向、`bow_rotation_deg` 的基准偏航
  全部由实测轴推出来，不要照抄别的枪。文档里要写清「出膛方向是局部 -X → 相机 +X 所以基准 yaw 180」。
- 分件诊断用 `combine_meshes=False` 逐个 section 导出再量，能区分「网格真的没弦」还是「弦烘在网格里」；
  必要时用 Fab 商店缩略图判读（`read_image`），比猜材质槽名快。
- 弦到底烘在哪个材质槽，只能进编辑器逐个隐藏确认——这是留到编辑器的待办，不要在后台瞎填。

### 5.8 headless Python 字段位置

- `import_uniform_scale` / `auto_generate_collision` / `build_nanite` 在 `FbxStaticMeshImportData` 上，**不在 `FbxImportUI`**。
- `AssetImportTask` 没有 `errors` 属性；导入结果靠导入后 `LoadObject` + 量包围盒自证。
- `USkeleton` 不再向 Python 暴露骨骼名查询；C++ 侧也拿不到 `GetRefSkeleton`，改用 `USkeletalMeshComponent::DoesSocketExist("hand_r")`。
- 每个探针段落单独 try/except 并把结果写盘：崩溃发生在测量与 `task.save=True` 之后时，资产仍是有效的，别因此重导。
- 后台跑法：`UnrealEditor-Cmd <uproject> -run=pythonscript -script=<绝对路径> -unattended -nop4 -nosplash -abslog=...`，
  外面套 `Tools/AssetPipeline/mcp_call_codex.ps1` 的批次互斥（本案封装成 `SourceAssets/<task>/Scripts/run_headless.ps1`，
  有 FPSGAME 的 UE 进程活着时它直接拒跑）。

### 5.8 C++ 编译陷阱（本轮全部踩过）

| 症状 | 真实原因 | 做法 |
| --- | --- | --- |
| `FString::CreateParseDelimiter` 未定义 | 5.8 已移除 | `Text.ParseIntoArray(Parts, TEXT(","), false)` |
| `FParse::ParseVector` 未定义、`LexFromString(FVector)` C2665 | 5.8 `String/LexFromString.h` 只管标量 | 自己写 `"x,y,z"` 解析函数 |
| `TAutoConsoleVariable<FVector>` 编译失败 | 只支持标量／字符串 | cvar 用 `FString`（`"0,0,0"`），运行时自己解析 |
| `USkeleton::GetRefSkeleton` 不可访问 | 不再公开 | `USkeletalMeshComponent::DoesSocketExist` |
| `GetSkeletalMesh()` 未定义 | 改名 | `GetSkeletalMeshAsset()` |
| `FRotator::ClampAxis()` 未定义 | 改名 | `Clamp()` |
| `FHitResult::GetBoneName()` 未定义 | 改成字段 | `Hit.BoneName` |
| C4458 遮蔽类成员 | 参数名撞上 `USceneComponent::bVisible` 等继承字段 | 参数用 `bInVisible` 前缀 |
| C2665 三元两侧类型不一致 | `TObjectPtr` 与裸指针混用 | 两侧都 `.Get()` |
| `TObjectPtr::Reset()` / `FName::Reset()` 未定义 | 无此方法 | 赋 `nullptr` / `NAME_None` |

## 交付边界

- Fab／第三方包：商用授权 ≠ 可再分发。原始 `.fbx` 与导入出的 `.uasset` 由 `.gitignore`（`/Content/*`、`*.fbx`、`*.log`）挡在仓库外，
  提交的是**作者脚本 + 实测回执 + 文档里的许可表**（来源 uid、发布时间、EULA 结论）。
- 开发期自动发放（首次进世界送一把弓 + 24 支箭）必须写进文档，并说明它只是开发便利钩子，不是正式获取途径。
- 弓不进 `FPSGAMECharacterProfile.cpp` 的枪械 definition 白名单，枪械视模因此保持隐藏、弓自己出画。
- 弹道投射物沿用既有口径：分步推进（单步 ≤ 60 cm）+ 球形扫掠 `ECC_Visibility`，命中走 `ColdSteelSkills::ApplyHit` 唯一入口，
  再 `NotifyConfirmedWeaponHit` 出反馈；插地 8 s 并按 `Hit.BoneName` 挂到被击组件。
- 屏幕状态行复用 `UColdSteelPickupPrompt`，不新开 HUD 部件。
