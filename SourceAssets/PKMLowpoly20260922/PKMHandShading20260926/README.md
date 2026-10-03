# PKM 左手小臂"脏条纹"离线诊断（2026-09-26，渲染侧子代理）

**结论先行：本轮不改任何代码。** 时间线取证 + 代码取证把候选收敛到一条主线：

> **第一人称手臂从不投影（自阴影在代码上不可能）；但第一人称下"看不见的世界身体 +
> 世界武器/装备副本"以 `bCastHiddenShadow=true` 持续向 VSM/Lumen 投影，而第一人称手臂
> 正常接收这些阴影。换弹时世界身体播 `Rifle.Reload`、世界 PKM 大枪身副本与视模手臂占据
> 同一片空间——隐藏投影体落在可见小臂上，就是"深色斜带、边缘发脏、三种外观同屏、
> 换弹最明显、跟着手臂走"的机制。**

案发时（用户首报时刻）所有皮肤细节贴图都是 32×32 占位图或尚不存在（§3 时间线），壳体网格
也尚不存在——贴图侧与壳体侧在案发时刻**物理上不在场**，无法是首报条纹的成因。这是比
Sprint47"在体证伪"更硬的排除。

决定性检验只需用户 10 秒控制台操作（§6 T1/T2），零构建零代码；确认后的修法涉及"世界身体
投影合同"的政策取舍，超出本子代理硬约束，列成决策菜单交用户拍板（§7）。

另：确认父会话转来的贴图状态（活体 SkinMicro=各向同性版、还原导入未执行）——合并点由
父会话补还原导入，本轮未动任何贴图/资产。

---

## 1. 着色输入链完整还原（任务 a）

运行时 PKM 默认（native_bare_arms=true、未穿模块化衬衫/手套）显示的是**烘焙进
`SK_PKM_Manny_Modular` 的 V7 裸臂**，臂部槽位材质 = `MI_BareNative_Default`；换装路径的
`MI_BareFamily_Arms` 与其共享同一 HLSL 与贴图。链条：

- HLSL：`Tools/ModularOutfit/skin_surface_v5.hlsl`（节点链构建
  `Tools/ModularOutfit/import_unified_skin_surface_m4.py:77-124`）
- 派生：`M_M4UnifiedSkin_Forearm` →（`import_bare_upperarms_m4.py:24-38`，覆盖率常量
  (1,1,0,0)，布料分支被编译器删除）→ `M_M4FullBareArmSkin` →
  （`import_bare_arms_family.py:51-87`，RestPosition/RestNormal 改接 UV1/2/3）→
  `M_BareFamily_Arms`；`M_BareFamily_Hands` →（`bake_native_bare_defaults_v7.py:67-85`，
  ForearmMode 接顶点色 R + SOFT_PALM/ForearmMode 法线补丁 :76-78）→ `M_BareNative_Default`

**小臂像素**（ForearmMode=1）的实际取值：

| 输出 | 表达式（skin_surface_v5.hlsl 行号） | 空间变化来源 |
|---|---|---|
| BaseColor | `WristTint(.372,.232,.182) × (1+broad·.035·forearmVariation) × lerp(1, 2·ColourDetail, .55·fade)`（:81-85） | broad ±1.75%；**ColourDetail ±~13%**（:77-80，rest 空间三平面，8 cm tile） |
| Normal | `rnm((0,0,1), detail)`，detail 由 SkinMicro.rg 经 dual-tangent 映射（:66-75） | SkinMicro（Sprint47 在体证伪 + §3 案发时占位） |
| 视差位移 | SkinMicro.b，限幅 0.24 mm（:56-65） | 同上 |
| Roughness | `.49−.04·palmar+.015·broad+(SkinMicro.a−.48)`，clamp[.30,.64]（:86-89） | SkinMicro.a（同证伪） |
| Opacity(次表面) | `.10` 常量（:102，SSP mfp .15 cm Burley） | 无 |
| Specular/Metallic | `.35`/`0` 常量（import_unified_skin_surface_m4.py:116-117） | 无 |
| AO/cavity | **材质链上不存在**（无 AO 输入、无 cavity 贴图） | — |

`fade=1−smoothstep(24,96,footprint)`（:30-31）：细节只在极端近距满强度——与"极端近距截图"
吻合。程序化项中不依赖贴图的只有 broad 正弦（±1.75%、波长 ~2.7 cm，宏观斑块量级）与
palmar/forearmVariation 平滑渐变——**都产生不了毫米级"脏条纹"**。

## 2. 阴影链（任务 b）——谁投影、谁接收

当前配置（Config/DefaultEngine.ini:19-33）：**VSM**（r.Shadow.Virtual.Enable=1）+ **Lumen GI/
反射**（r.DynamicGlobalIlluminationMethod=1、r.ReflectionMethod=1）+ r.RayTracing=True（RT
proxies 开）+ Substrate；r.AllowStaticLighting=False。

| 部件 | 投影 | 接收 | 证据（当前工作树行号） |
|---|---|---|---|
| 第一人称视模（AKMViewmodel 持 SK_PKM_Manny_Modular=枪+裸臂） | **false**：构造关死（FPSGAMECharacter.cpp:219，09-10 起从未变过，git -S 证实），且 **UpdateOwnerVisibility 每 0.2 s 对相机下所有 primitive 重申 `ApplyShadowFlags(false)`**（FPSPlayerBodyComponent.cpp:262-273，:272） | 正常接收世界阴影（无接收侧排除；FPPT 未设=同场景光照） | 左列 |
| 第一人称装备壳（衬衫/手套 Presentation，挂视模下） | 照抄 Source=false，且同被 :272 的 0.2 s 重申覆盖 | 正常 | FPSModularOutfitComponent.cpp:122-124,299-300 |
| **世界身体**（第一人称 OwnerNoSee 隐藏） | **CastShadow=true + bCastHiddenShadow=true → 隐藏仍投影** | — | FPSPlayerBodyComponent.cpp:201-202；注释 :66-68 |
| **世界武器副本**（挂 hand_r，臂段隐藏、枪身段可见并投影） | 同策略 `ApplyShadowFlags(BodyShadow && !Stowed)`，第一人称默认 true | — | FPSPlayerBodyEquipment.cpp:44-54,77-99（:84 臂段进 HiddenMaterials）,246-262 |
| **世界装备壳副本**（穿衬衫/手套时） | 同上（ApplyWorldBodyShadow 覆盖 OutfitMeshes） | — | FPSPlayerBodyComponent.cpp:111-120 |

**推论 1：字面"视模自阴影/shadow acne"不成立**——投影体缺失（构造期 false + 每 0.2 s 重申，
09-10 起如此）。Sprint47 的"首要嫌疑=自阴影"须修正为下面的跨体投影。

**推论 2（机制 A，代码级确认、自 09-22 19:32 世界身体上线起常开）：** 第一人称下隐藏的
世界身体+世界 PKM 副本（+世界装备壳）向 VSM/Lumen 投影，可见的第一人称手臂接收。
换弹时两者空间重合度最高：世界身体播 `Rifle.Reload`
（FPSPlayerBodyAnimInstance.cpp:395-399；Content/ColdSteelData/player_body.json:39），
世界 PKM 大枪身（机匣/枪管/弹链，臂段已隐藏但武器段投影）就贴在视模左小臂旁。
**PKM 特异性也由此解释：PKM 是最大最重的枪，世界副本是最大的近身投影体**；
换弹动作又把它抬到左小臂正上方/侧上方。投影体与接收体刚性同随玩家 →"条纹跟着皮肤走、
放大缩小跟着皮肤"同样成立（与 Sprint47"推理更正"同理）。阴影内外亮度差 ≫ 任何贴图通道
能给的对比 → 解释"发白的手 / 深灰褐小臂 / 橙色斑块"三种外观同屏与"有东西把手臂压暗了"。
机制 A 自 09-22 存在，覆盖用户首报至今的全部时间线。

**推论 3（机制 C，A 的 Lumen 伴生）：** 隐藏身体/副本同时在 Lumen 场景里遮挡 GI
（r.AllowStaticLighting=False，全靠 Lumen），给手臂叠加接触性压暗。`fps.body.WorldBody 0`
可连同 A 一起关掉，`fps.body.WorldBodyShadow 0` 只关直接光阴影——两者对比可分离 A/C。

## 3. 时间线取证：案发时谁在场（父会话转来证据 + 本轮独立核实）

| 时刻（2026-09） | 事件 | 证据 |
|---|---|---|
| 09-10 16:02 | 视模 CastShadow=false 进库，从未改过 | git log -S（唯一命中=初始导入提交 0bf10ae9） |
| 09-22 19:32 | 世界身体上线，bCastHiddenShadow=true | git log -S（90d6afd3） |
| ≤09-24/25 | **用户首报条纹**（Sprint47 开跑前） | Sprint47/README |
| 案发时 | **三个 SkinMicro 变体全是 32×32 占位图** | import_micro_receipt.json `size_before:[32,32]`（父会话发现，本轮复核） |
| 09-24 23:29 / 09-25 00:17 | ColourDetail 才首次成为真图（RefinedV3 / WristV4） | uasset created=written（本轮测量） |
| 09-25 09:32 / 16:44 / 21:32 | FittedSleeves / FittedFieldGloves / HuntFieldGloves 的 PKM 壳体网格才存在 | uasset created |
| 09-25 22:15 | V7 裸臂烘进 SK_PKM_Manny_Modular（当前默认链上线） | uasset created |
| 09-25 23:13 | 各向同性 SkinMicro 导入（唯一一次真图导入）→ 用户实测条纹无变化 → 回滚源 PNG，**还原导入从未执行，活体至今是各向同性版** | receipt + uasset mtime/size 逐项吻合（WristV4 10216602 B = 回执 9977 KB） |
| 09-25 23:54 | 并行会话把 PKM gloves 配置改指 FittedFieldGlovesV1 | 父会话通报 |

**判定：**
- **SkinMicro（法线/高度/粗糙度 detail）**：案发时=占位图，现在=各向同性版仍在报条纹 →
  **双重证伪，彻底出局**（与父会话结论一致）。
- **ColourDetail（颜色梳纹）**：若首报在 09-25 00:17 前 → 案发时不在场，出局（对首报而言）；
  若首报在 09-25 白天后 → 在场。但无论哪种，它只有 ±13% albedo 对比，**解释不了"深灰褐 vs
  发白"的大压暗**，只能是近距细纹的叠加贡献者，不能是主因。它至今未被任何测试触碰，
  保留为次级候选（本轮已量化：2.27×@82.5°、~1.9 mm 间距，§4）。
- **壳体/装备层**：首报时 PKM 壳体网格全部不存在（09-25 09:32 后才有）→ 对首报出局。
  当前若用户戴手套：第一人称壳体不投影（§2），贴合式壳体只能给出腕口材质边界，
  给不出小臂中段"皮肤上的条纹"；穿衬衫则小臂段 [0,1] 被隐藏、看到的是布料不是皮肤。
  **世界侧**壳体副本倒是投影（§2 表末行）——那是机制 A 的一部分，不是独立壳体候选。
  手套配置 23:54 改指向只影响"戴不戴、戴哪双"，不改变上述结论。
- **程序化项（不依赖贴图）**：broad ±1.75% 太弱；cloth/weave 分支在 V6/V7 臂材质里被常量
  覆盖率编译删除。无幸存项。
- **幸存且案发时在场的光照侧机制 = A（+C）**，且是唯一能给出大对比压暗的机制。

## 4. 本轮量化测量（analyse_colour_detail.py，方法=Sprint47 analyse_grain 原样）

| 对象 | peak/iso | 主方向 | 谱熵 | 主导条纹间距 |
|---|---|---|---|---|
| 活体 ColourDetail（WristV4，luma） | **2.27×** | **82.5°** | 0.954 | ~1.9 mm |
| 源 COLOR 扫描（线性 luma） | 2.21× | 82.5° | 0.957 | ~1.9 mm |
| 回滚后 SkinMicro 高度场（方法对照，应回 2.12×@62.5°） | 2.12× | 62.5° | 0.948 | ~2.0 mm |

albedo 因子（shader 忠实 `1+.55·(2·tex−1)`）：p1 0.864 / p50 0.995 / p99 1.159，
p95/p5=1.25×（σ=1 模糊后 1.22×）。→ ColourDetail 确实是一层贴肤、随皮肤缩放、只在近距
满强度的方向性梳纹，但对比上限 ~1.25:1。

## 5. 资产状态分歧（父会话已知悉并接手）

活体 `Content/.../OriginalShapeBareM4WristV4(/RefinedV3)/T_M4OriginalShape_SkinMicro.uasset`
= 09-25 23:13 各向同性版（被否决内容）；源 PNG 已还原、还原导入未执行。合并点由父会话
补还原导入（父会话通报），本轮未动贴图。ColourDetail 源 PNG 与活体一致（从未被改）。

## 6. 决定性检验清单（交给用户；全部零构建、零代码、10 秒级）

按序做，哪一步条纹消失/变化，机制即定案：

1. **T1（判 A-直接光阴影）**：复现条纹（PKM 换弹、近距），控制台
   `fps.body.WorldBodyShadow 0`。灰褐层+条纹消失或明显变淡 → **A 成立**；`1` 恢复。
   （该 CVar 就是为此准备的 A/B 开关，FPSPlayerBodyComponent.cpp:69-77。）
2. **T2（判 A+C 全光照侧）**：`fps.body.WorldBody 0`。T1 无效而 T2 有效 → 压暗来自
   Lumen GI 遮挡（C）而非直接光阴影；`1` 恢复。
3. **T3（判光照 vs 贴图）**：同一姿势不动，只改太阳角度（改时间/转身）。条纹位置与对比
   跟着变 → 光照侧（A/C）；**完全不变** → 贴图侧（转 T4）。
4. **T4（判 B-ColourDetail）**：编辑器把 `MI_BareNative_Default` 与 `MI_BareFamily_Arms`
   的标量 `ColourDetailStrength` 0.55→0，近距看小臂：~1.9 mm 细梳纹消失 → B 是细纹贡献者
   （改回即回滚）。
5. **T5（壳体自证）**：卸下手套/衬衫再复现。条纹依旧 → 壳体出局（第一人称壳体本就不投影）。
6. 附：量截图暗带/亮带亮度比：≈1.1–1.3 且随光照不变 → B 主导；>1.5 且随光照变 → A 主导。

## 7. 确认后的修法决策菜单（均触碰"世界身体投影合同"或共享资产，须用户拍板；本轮未动手）

- **A 成立（预期大概率）**：引擎没有"只不接收某投影体"的接收侧开关（bSelfShadowOnly 是
  投影体侧、LightingChannels 是灯侧，均不适用），所以不存在"零触碰世界身体投影"的修法。
  可选项：
  - **F1**（最小 diff）：第一人称本地玩家的世界身体/副本停投影（即把
    `ShouldWorldBodyCastShadow()` 的 FirstPersonOwner 分支默认改为 false，等效于常开
    `fps.body.WorldBodyShadow 0`）。代价：**第一人称看不到自己的地面/墙面投影**——
    这正是 bCastHiddenShadow=true 的设计目的，属玩法视觉合同变更。
  - **F2**（外科式）：只压制与视模空间重合的投影体——第一人称下隐藏世界身体**手臂段**
    （section 级，本地渲染态，不影响远端玩家看你的身体；躯干/腿/世界武器投影保留）。
    改动集中在 FPSPlayerBodyComponent/Equipment 的可见性刷新路径。代价：第一人称下
    自己手臂的地面阴影消失（但那条阴影本来就和可见视模手臂错位，属双重影 bug）。
  - **F3**：给视模加独立光照（专用灯+关太阳光影响）——工程量最大，改第一人称光照观感，
    不推荐首选。
  - T1/T3 结果决定 F1 vs F2（若压暗主要来自世界**武器**副本而非身体手臂，F2 需扩到武器段）。
- **B 成立/叠加**：复用 `Tools/ModularOutfit/skin_grain.py::isotropise()` 作用于
  bake_refined_skin_m4.py:30-34 的 ratio 场，重烘+编辑器批次重导入（共享皮肤资产、全局
  外观改动，需用户确认方向）；或最小替代：仅把 V7 两个 MI 的 `ColourDetailStrength`
  调低/置 0（近距皮肤色变细节变平）。两者都超出本子代理写入范围（资产/编辑器侧）。

## 8. 本轮未改代码的理由与并发说明

1. 任务规则：无决定性归因证据不动手（Sprint47 教训）。§6 的 T1–T3 十秒定案，先测后改。
2. A 的所有修法都触碰受保护的"世界身体投影"合同 → 必须用户决策，不存在合规的单方面最小修。
3. B 的修法在共享资产/编辑器侧，超出本子代理写入范围（仅 Source/FPSGAME/Characters/ 与
   诊断目录）。
4. **并发修改观测**：工作期间另一会话对全库做了大批量改动（git status 从本轮开始时的
   ~8 个文件涨到 180+ 文件；`FPSGAMECharacter.cpp` mtime 09-26 01:20:59，行号整体 +5）。
   本轮**零写入 Source/**，所有引用已按当前工作树复核（视模 CastShadow=false 现于
   FPSGAMECharacter.cpp:219，装枪 :470；PKM BoundsScale=2 :468——仅包围盒，与阴影无关）。
   FPSPlayerBodyComponent.cpp / FPSModularOutfitComponent.cpp / FPSPlayerBodyEquipment.cpp
   的未提交改动未触及阴影语义（diff 过滤核实）。

## 文件

- `analyse_colour_detail.py` — 本轮测量脚本（只读源资产）
- `colour_detail_report.json` — 原始测量数据
- `colour_factor_preview.png` — albedo 因子作用在中棕底色上的目视预览（2048²=8 cm 皮肤）

本轮未构建、未启动编辑器、未进游戏、未跑 PIE/截图；按用户规则未做测试与验收。
