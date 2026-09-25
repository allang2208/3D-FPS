# 第一人称弓：部件表与相机空间组件

当前暗纹猎弓为 ContactV9 视模和八段动作，表现版本 9；ArmsV4 提供共享骨架／装备，ArmsV2 提供已分离弓体、箭和材质。V9 已保存，仍待用户游戏确认。
绑定、握把掌向、指腹接触和掌面修补读 [弓手型与弦接触](../../ue5-fps-arms-animation/references/bow-hand-string-contact.md)。本案例全过程、失败原因及恢复范围见工程 `Docs/Weapons/dark-bow-publication-v9-20260925.md`；历史版本号不作为当前选择依据。

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
- 材质覆盖用**组件级** `SetMaterial(Index, Material)`，空槽名表示本部件的材质 0，覆盖同时应用到细杆。
  只有烘焙弦独占材质槽时才可隐藏整槽。本例旧弦与握把、端件共用材质，已在独立弓体副本中分离 124 个弦三角，保留原资产。
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
- 刷新走**表现签名**：`PresentationSignature()` 包含各槽 mesh/material/hide_slot、视模、动画前缀、箭镞、音效、箭种及旧平铺键。
  签名没变＝纯数值/参数改动，只重算数值与部件，**不重载资产、手上不闪帧**；变了才异步重载并重装。
- 仅用户明确要求检查时运行 `python Tools/Bow/check_bow_consistency.py`。它校验键集合、`"x,y,z"` 可解析、
  `/Game` 路径在 `Content/` 真的落盘、槽清单齐三件且每槽键完整、纯程序化槽不能既无 `_rods` 又无 `_mesh`、
  动画前缀对应的八段资产、箭种是否登记在 `ammo_types.json`。空 `hide_slot` 是合法的本槽材质覆盖，不应报错。

## 程序化几何与占位

- 占位用引擎 `/Engine/BasicShapes/Cylinder`（轴向 +Z、长 100、半径 50）：拉伸时**粗细由 `_radius_cm` 决定、长度由端点决定**，
  两个自由度分开，别把半径也按长度缩放。
- 给了正式网格时按其 `GetBounds()` 自取轴（`BoxExtent.X > BoxExtent.Z` → 轴 +X）与作者长度，**不再拉伸粗细**。
- 只补偿长度轴上的中心；不对横向包围盒中心做平移，否则不对称尾羽会使箭杆脱离弦结点。
- 投射物 Actor 原点在箭尖，网格沿后方展开；弦上箭与飞行箭保持同一根长轴。
- 视模子件统一口径：`NoCollision` / 不影响导航 / 不投影 / `SetOnlyOwnerSee(true)` / 默认隐藏。
- 挂点组件必须**先注册父挂点再建子件**，否则子件注册时拿不到有效父变换。

## 参考动作与原生 Bow 骨架

片段长度只能提供节奏信息，不能代替参考动作制作。本例已提取 Sparrow 的手／肘轨迹：

- `reference_*_clip_seconds` 记录原始片段时长，`draw_seconds` 是作者选择的游戏时长。拉弓的手部间距归一为 17 点 `draw_curve`；骨长与接触由 V7 裸臂的两段 IK 约束，不拉伸手臂迁就第三人称姿态。
- 本例新建 `SK_Bow_BareArmsV7_Skeleton` 和八段 Idle／Ready／Equip／Nock／Draw／Hold／Release／Run；Sparrow 不作为运行时骨架。保留 V7 表面、权重分布与皮肤，衣袖／手套按 Bow 原生参考姿态派生。
- 弓体挂 `bow_grip`，弦触点挂 `bow_nock`，不能以手腕原点代替指端接触点。
- 播放合同：只 `PlayAnimation` 一次 → `SetPlayRate(0)` → 每帧 `SetPosition(秒)`（循环段 `Fmod`，单向段 `Clamp`）→
  `TickAnimation(0, false)` → `RefreshBoneTransforms()`。**每帧重新起播会让手臂停在片段开头**（与采集工具同一口径）。
- 阶段映射：按阶段时间比例乘实际片段全长。Draw 动画内部已有参考拉距曲线，不能再次用 `DrawFraction` 重映射，否则曲线重复应用。
- 先手动采样、刷新手臂，再查询标记更新弓弦；Release 与 Recover 连续采样同一段，不在 Recover 重播开头。阶段过渡在局部骨段空间混合，保持骨长。
- 放箭后弦独立回弹至弓档，右手继续随动；未搭箭 Idle、已搭箭 Ready、满拉 Hold 分开。
- 动画资源加载完成前不可进入射击。异步回调核对实例及表现签名，避免旧弓回调覆盖新装备。
- 制作完成不等于运行／视觉验收；当前 ContactV9 资产已保存，未运行游戏，由用户测试。

## UE 5.8 实测与导入要点

- **不要相信文件名里的尺寸**。FBX 常按作者单位导入（本案原始包 414 cm 高，不是标称的 148 cm）；
  先量包络再按最长轴归一，并把 `import_scale`、归一后 `size_cm`、`origin_cm`、材质槽写进 `ue_import_readback.json`。
- 静态网格的**长度轴不一定是 X**：本例长轴 Z，实际烘焙弦 X≈-21.46、Y≈-0.935，箭朝局部 +X，静态回落 yaw 0。保留作者握把原点；不要仅凭包络极值推断弦侧。
- 分件诊断用 `combine_meshes=False` 逐个 section 导出再量，能区分「网格真的没弦」还是「弦烘在网格里」；
  必要时用 Fab 商店缩略图判读（`read_image`），比猜材质槽名快。
- 烘焙弦可通过 GeometryScript 的网格连通性、顶点坐标和材质 ID 在后台分离；无须为此启动交互编辑器。已有编辑器时用批次互斥保存本任务资产。

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
  提交作者脚本、配置、文档和归档散列元数据。含网格／骨骼／密集姿态的 JSON 及导入回执仍留在本机，不能仅因扩展名是文本就公开。
- 开发期自动发放一把弓与 24 支箭使用同一库存事务；只有首次新建弓才发箭，不能每次箭袋空了自动补充。该钩子不是正式获取途径。
- 搭箭只预留表现，成功发射才扣箭；打断不能吞箭。旧实例仅迁移表现字段，保留强化／战斗数值与自定义部件，清除继承的枪械弹匣数值。
- 发射伤害、强化预览与 Tooltip 共用 DamageParts；箭种倍率／穿透在发射快照进入战斗系统。弓术攻速缩放拉满耗时，动画仍采样全段。
- 弓不进 `FPSGAMECharacterProfile.cpp` 的枪械 definition 白名单，枪械视模因此保持隐藏、弓自己出画。
- 弹道投射物沿用既有口径：分步推进（单步 ≤ 60 cm）+ 球形扫掠 `ECC_Visibility`，命中走 `ColdSteelSkills::ApplyHit` 唯一入口，
  再 `NotifyConfirmedWeaponHit` 出反馈；插地 8 s 并按 `Hit.BoneName` 挂到被击组件。
- 现有弹药 HUD 显示拉距、箭袋与搭箭状态；PickupPrompt 只留短时失败反馈。不要复制一套常驻调试状态行。
- 该系列尚无弓臂形变、专用音效／图标、箭拾回、独立改造 UI／第三人称动作；部件接口已存在不代表这些内容已完成。
