# 树木生命值与按伤害伐木（2026-09-25）

用户要求（2026-09-25）：**给树木像怪物一样设置血量，斧头砍树按血量扣血，血量归零树木才倒下**，
并要求开发时注意性能。本文记录本次升级的口径、改动文件与未完成项。

替代关系：砍树不再是「累计 3 次有效命中即倒」，改为生命值口径。岩块与表土的命中数口径
保持不变（见文末「以后要给岩块也上血量」）。

## 1. 结算口径

| 项 | 规则 |
| --- | --- |
| 生命上限 | 树种基础生命（A/B/C/D）× 实例尺寸系数（候选点缩放 .68–1.08 映射到 .85–1.25）× `fps.Harvest.TreeHealthScale`（默认 1） |
| 单次挥砍伤害 | 工具**自卫伤害面板** `FProductionToolStats::Damage.Total()`（含改造、附魔、强化与角色物攻）× 「所需有效命中」改造折算倍率，最低 1 点 |
| 命中改造折算 | 出厂 3 挥改成 2 挥（`harvest_hits_add=-1`）即 ×1.5：形态上等于每次多打半次，标定伤害下「3＋加值」仍逐次对应当前挥砍数 |
| 倒树条件 | 剩余生命 ≤ 0 的那一挥才触发倒树事务；此前每一挥只提交生命进度，不产材料、不倒树 |
| 暴击与浮动 | 树不吃暴击与弱点，伤害不做随机浮动，提示栏的「还需 N 挥」就是真实挥砍数 |

标定参考（`Production/ProductionTreeHealth.cpp` 内的常量表）：1 级未加点角色手持出厂伐木斧时
自卫伤害 ≈ 12（武器公式）＋ 10（角色物攻）＝ 22/挥，于是 A 树 3 挥、D 树 5 挥，与旧「三次有效命中」
手感接近；树木尺寸系数与改造再在其上浮动。

调平衡不用重编译：`fps.Harvest.TreeHealthScale` 整体缩放生命值（1 = 出厂），树种基础生命表在
`ProductionTreeHealth.cpp` 顶部。

## 2. 存档口径

- 新增 `FColdSteelProfile::TreeHealth`：`world GUID:v1:0:candidate -> 剩余生命比例 0..1`，缺省＝满血。
- **存比例不存绝对值**：以后调树种生命、加倍率或新增树种，旧档「砍了一半」仍是砍了一半，
  不需要迁移遍历，也不会把半血的树读成满血或濒死。
- 旧档（只有累计命中 1..3 的 `HarvestProgress`）在读取时按同一进度换算（`1 − 命中/3`），
  读一次即生效，不写迁移批处理。
- 采尽的那一挥仍补写 `HarvestProgress = 出厂 3 次` 并登记 `TreeGrowth`：世界的 `IsProductionDepleted`、
  树桩重建、PCG 补生与旧档迁移仍按命中数口径读它们，不因为换了生命值口径而失效。
- 成熟的重生树按满血读（与 `HarvestProgress` 的回归口径一致），不重写记录。

## 3. 性能

本次没有新增任何逐帧工作：

- 生命上限在 `ResolveProductionResource` 里算一次，跟着资源快照走；结算与提示栏都读这一份，
  没有第二处换算，也没有为读数值再去加载资源。
- 挥砍路径只多两次 `TMap` 查找与几个乘法（`TreeHealthRatio` + 伤害折算），随原有的
  「一次 `Snapshot` + 一次 `CommitState`」事务提交，没有新增存档往返。
- 瞄准提示仍是 **0.15 s 一次** 的既有刷新节奏，只把 `1 / 3` 换成 `生命 34 / 62 · 还需 2 挥`。
- 不给树加 Actor、组件、Tick、血条控件、射线或每帧查询；血条不做，生命值走提示栏文字。
- 存档增长有界：每棵被砍过的树一条 `TreeHealth`（与旧口径每棵树一条 `HarvestProgress` 同量级），
  采尽时同时写 `HarvestProgress` 与 `TreeGrowth`，与本次改动前一致。

## 4. 改动文件

- 新增：`Source/FPSGAME/Production/ProductionTreeHealth.{h,cpp}`（树种生命、挥砍伤害、挥砍数、CVar）。
- 资源快照：`Production/ProductionResource.h` 新增 `MaxHealth`（>0 走生命值口径，0 走命中数口径）；
  `WorldGeneration/TemperateHillsProduction.cpp` 在解析树木资源时填上限。
- 结算：`UI/ColdSteelProductionTools.cpp` 新增 `TreeHealthRatio` 与 `CommitTreeStrike`，
  `CommitHarvestStrike` 按 `Layer==0 && MaxHealth>0` 分流；`UI/ColdSteelInventoryTypes.h` 新增存档字段。
- 呈现：`Production/ProductionToolComponent.cpp` 提示栏显示生命与预计挥砍数。
- 文案：`UI/ColdSteelItemTooltipData.cpp`、`ColdSteelItemTooltipSummary.cpp`、`ColdSteelItemTooltipFormula.cpp`、
  `ColdSteelCodexPage.cpp` 的伐木斧条目改为「伐木伤害 / 标准树所需挥砍」；矿镐条目（工作台行名与目录
  `effects` 逐字一致的约束下）保留「所需有效命中」，只在说明段补一句斧与镐的口径差异。

## 5. 明确不做与后续

- 本轮只给树木上血量。以后要让岩块也吃伤害：在 `ResolveProductionResource` 给 `Resource.MaxHealth`
  填上限即可，`CommitHarvestStrike` 的分支与提示栏都已经按上限分流，命中数口径的岩块/表土代码不用动。
- 没有做血条控件、伤害飘字、树皮受击材质或倒地前摇晃动作；这些属于表现层，需另行授权与制作。

## 6. 构建与验收状态（2026-09-25 21:22）

- **UHT 已按新头文件重跑**：`Intermediate/Build/Win64/FPSGAMEEditor/FPSGAMEEditor.uhtmanifest`，
  `Saved/BuildEditor/build-treehealth-20260925-2110.log` 记 `UHT processed FPSGAMEEditor ... (3 generated files written)`；
  重跑后 `ColdSteelInventoryTypes.generated.h` 的 `..._175_GENERATED_BODY` 与新行号一致。
- **改动过的翻译单元逐个语法核对零错零警**（本模块自己的 `.cpp.obj.rsp` + `cl /nologo /Zs`，工作目录
  `Engine/Source`，输出到系统临时目录）：`ProductionTreeHealth.cpp`（新文件，按同构文件复制 rsp）、
  `ColdSteelProductionTools.cpp`、`ProductionToolComponent.cpp`、`ColdSteelItemTooltipData/Summary/Formula.cpp`、
  `ColdSteelCodexPage.cpp`、`M4GunsmithSelectedDetails.cpp`、`TemperateHillsProduction.cpp` —— 9/9 退出码 0。
  注意：改过带 `GENERATED_BODY()` 的头文件后，这条路径在 UHT 重跑**之前**必然报假错（`C2143/C4430`，
  行号宏对不上），本次先跑 UHT 再核对。
- **整模块构建链接成功**：`Saved/BuildEditor/build-editor-expedition-altar-2-20260925.log`（同一工作树的
  并行增量构建，含本次全部改动）100 个动作、`Link UnrealEditor-FPSGAME.dll` → `Result: Succeeded`；
  仅有的告警来自其他目录既有代码（`C4996`/`C4305`），本次改动的文件零告警。
- **编辑器全部关闭后由本任务完整跑通一次**：`Saved/BuildEditor/build-treehealth-final-20260925-214716.log`
  —— UHT 重跑（`-WarningsAsErrors`，新头文件通过）→ 19 个编译动作（含 `ColdSteelProductionTools.cpp`、
  `ProductionToolComponent.cpp`、`TemperateHillsProduction.cpp`）→ `Link UnrealEditor-FPSGAME.lib/.dll`
  → `Result: Succeeded`，退出码 0，零错误零告警，总耗时 813 s（机器被并行的 ripgrep 全树扫描占用，
  非构建卡死）。`Binaries/Win64/UnrealEditor-FPSGAME.dll` 时间戳 22:00:50、13,655,552 字节，
  仍搜到 `fps.Harvest.TreeHealthScale`（UTF-16LE）。
- **代码确实进了二进制**：按 UE 宽字符字面量口径在 DLL 里搜到 `fps.Harvest.TreeHealthScale`
  （UTF-16LE 命中；ASCII 不命中属正常，勿据此误判）。
- **未做运行验收**：依用户规则没有启动游戏、PIE、性能采集或截图。挥砍手感、提示栏读数、树种生命与
  尺寸系数的实际手感、旧档读入后的半血树表现，全部由用户实测确认。上文所有数值都是标定与推算，
  不是实测挥砍次数或实测帧数。

## 7. 实测反馈与修复：砍倒过的树打不掉（2026-09-25 22:3x）

**现象（用户实测）**：用斧头攻击树木不掉血、无法造成伤害。

**证据（读用户存档 `Saved/SaveGames/ColdSteelPlayer_A/B.sav`，USaveGame 带标签序列化，属性名与键都是明文字符串）**：

```
TreeHealth        : 1 条  → 92DC…:v1:0:ffffffe8fffffffe = 0.5369（斧头确实扣过血并已落盘）
HarvestProgress   : 8 条 layer-0 键（含上面这条）
TreeGrowth        : 同样的 8 条 layer-0 键（含上面这条）
```

即：**扣血、事务提交与存档都正常**，被砍的那棵树同时在 `TreeGrowth` 与 `TreeHealth` 里有记录
（＝砍倒过、又长回来的重生树）。

**根因**：`UColdSteelStatusModel::TreeHealthRatio` 里「成熟的重生树＝满血」这条判断排在读存档比例**之前**。
重生树一律命中该分支 → 界面永远显示满血；每次挥砍都从满血重算，写回同一个数（这正是存档里
0.5369 只出现一条、且不随挥砍次数变化的原因），树永远不会倒。用户世界里 8 棵 layer-0 树全部带
生长记录，所以试哪棵都一样。

**修复**：读顺序改为「有生命记录就以记录为准；只有比例 0 ＋ 已长成（＝确实被砍倒过）的重生树才读作
满血的新树；没有记录时才回退到旧档的累计命中换算」。被砍掉一半的重生树从此继续读自己的比例，
可以正常打完、正常倒下；已砍倒且未长成的树仍判 0（配合 `ResolveProductionResource` 的「正在生长」拦截）。

**遗留观感**：本次修复前，重生树被反复写入的 0.5369 会作为「已受伤」保留——那棵树会显示约 54% 生命、
少挥两下就倒。这是合法数值，不影响正确性；要清成满血需另做一次性迁移（当前不做）。

**构建状态（已补齐）**：修复所在翻译单元 `ColdSteelProductionTools.cpp` 编译通过
（`Saved/BuildEditor/build-treehealth-fix-20260925-223340.log` 的 `[3/15]`，obj 22:34:09 晚于源码 22:33:27）。
那一轮链接被并行会话当时正在编辑的 `Source/FPSGAME/WorldGeneration/FluidPresentationSubsystem.cpp`
（`C3861 GetGameInstance` 等 5 条错误）挡住（`Result: Failed (OtherCompilationError)`），按项目规则不代改他人文件；
该文件 22:37:19 修好后，并行会话的 `Saved/BuildEditor/build-20260925-223752.log`
（`[1/4] Compile FluidPresentationSubsystem.cpp` → `[3/4] Link UnrealEditor-FPSGAME.dll` → `Result: Succeeded`）
把含本修复的 obj 链接进了模块：链接响应文件
`Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME/UnrealEditor-FPSGAME.dll.rsp` 里同时列有
`ColdSteelProductionTools.cpp.obj` 与 `ProductionTreeHealth.cpp.obj`，`Binaries/Win64/UnrealEditor-FPSGAME.dll`
时间戳曾更新为 22:38:01、13,657,600 字节（晚于本修复源码 22:33:27）。
用户关闭编辑器后，本任务又完整跑通一次编辑器构建：
`Saved/BuildEditor/build-treehealth-verified-20260925-230513.log`
（`Build.bat` 先等并行 Game 目标构建让出互斥 → `[1/4] Compile AuthoredDungeonGenerator.cpp`
→ `[2/4]/[3/4] Link UnrealEditor-FPSGAME.lib/.dll` → `Result: Succeeded`，退出码 0，零错误零告警，309 s）；
最终 `Binaries/Win64/UnrealEditor-FPSGAME.dll` = 23:09:46、13,658,624 字节，`Binaries/Win64/FPSGAME.exe`
= 23:05:01（并行会话的 Game 目标构建，同样编译了本修复的 `ColdSteelProductionTools.cpp`）——
**编辑器与独立游戏两个二进制都含本修复**，PIE 或独立运行都会加载。
另外记一笔：本任务随后挂的「每 60 s 重试构建」脚本 12 次全部失败，但那是脚本自己的问题（PowerShell 把
`"-Project=$project"` 传成空值，UBT 在 0.3 s 内报 `The argument '-Project=' does not specify a valid file name`），
不是构建失败；直接用字面量路径调用 `Build.bat` 的写法才是可靠的。

**修复后的实测仍是空白**：用户 22:47–22:48 的 PIE 会话（`Saved/Logs/FPSGAME.log` 里的
`UEDPIE_0_L_TemperateHills_Initial`）加载的已经是含修复的 22:38:01 DLL，但存档在 22:49:19 被重写时
**字节与 22:28 完全一致**（`TreeHealth` 仍是那一条 0.5369、`TreeGrowth` 仍是那 8 条），
说明那次没有砍任何树，所以修复是否解决现象仍待用户实测确认。

## 8. 实测反馈与排查：树倒后变成三角形碎片（2026-09-25 23:5x）

**现象（用户实测，附截图）**：砍倒后"全程"如此——倒下的上半段叶片变成一片片**几米大的平面三角**（
纯色，浅绿／橄榄／棕，边缘是硬直多边形，没有叶片贴图、没有镂空），树干变成**尖刺状深色乱片**；
同图对照里**站立的树正常**，**树桩本体正常**，只有树桩顶面那块**发白**。

**截图判读（裁切放大 5× 后逐块看）**：三角是**平面着色多边形**，不是"叶片卡片丢了遮罩"——卡片丢遮罩
仍会带叶片贴图与叶形边缘。这个形态是**低模/代理几何**（经典 LOD 或回退网格）的典型外观。
树桩顶面发白＝默认材质。

**离线已排除（读 `.uasset` 明文，不启动引擎）**：

- 倒树网格 `SK_CutUpper_A` 引用了与原树**完全相同的 13 个 Megaplant 组合子部件**，骨架、材质槽名
  （`CutEndGrain`）、Nanite 设置名都在；倒树材质带的是真·黑杨贴图 `T_Black_Poplar_01_*`，与站立树一致；
- 落地特效资产引用齐全（尘土 `P_Destruction_Wood`、落叶 `FX_FallingLeaves` → `SM_Leaf_01/03` + `MI_Scatter_03`）；
- 四个变体"倒树/原树"体积比一致（A 33%、B 30%、C 33%、D 32%）→ **不是 A 变体独有的资产缺陷**。

**日志确证的两个真缺陷**（`Saved/Logs/FPSGAME.log`，用户实测倒下那一秒 `15:22:48`）：

```
LogMaterial: Warning: Material /Game/Items/HarvestTimber/M_FallingCutEnd ... missing usage flag Nanite!
             Default Material will be used in game.
LogMaterial: Warning: Material /Game/Items/HarvestTimber/M_TreeCutSurface ... missing usage flag
             InstancedStaticMeshes! Default Material will be used in game.
```

- `M_FallingCutEnd` 挂在 **Nanite 骨骼网格**的槽 2 上，却没有 `used_with_nanite` → 游戏里断面变默认材质；
- `M_TreeCutSurface` 画在**静态实例**（树桩）上，却没有 `used_with_instanced_static_meshes` → 树桩切面变默认材质（截图里那块发白）。
- 根因在制作脚本：`SourceAssets/HarvestTimber20260913/import_tree_sections.py` 第 18–23 行只设了
  `two_sided` 与 `used_with_skeletal_mesh`，从未设这两个标志；`build_falling_assemblies.py` 第 7 行
  也只给断面材质补了 `used_with_skeletal_mesh`。引擎侧 `USkinnedMeshComponent` 会先
  `AuditMaterials(..., true /* Set material usage flags */)` 再算 `bHasValidNaniteMaterials`，
  使用标志与渲染路径不匹配就会被替换成默认材质。

**本轮已做（离线，可复核）**：

- 新增 `Tools/Production/fix_harvest_material_usage_flags.py`：幂等补齐两个材质的缺失标志（改完重编译并保存，只动缺的那几个）；
- 加固制作脚本：`import_tree_sections.py` 按 `fade` 同时设 `used_with_nanite` / `used_with_instanced_static_meshes`，
  `build_falling_assemblies.py` 给断面材质补 `used_with_nanite`——重新走一遍制作不会再退回这个缺陷；
- `ProductionFallingTree.cpp` 增加一次性诊断（可 `fps.Harvest.TreeFallDiag 0` 关闭）：每次倒树打印一行
  `FALLDIAG mesh=… nanite_data=… force_disable_nanite=… lods=… predicted_lod=… slots=[…]`，
  用来钉死倒树到底走 Nanite 组合还是退化成经典 LOD／回退网格。该翻译单元 `/Zs` 语法检查通过（退出码 0，零错误零告警）。

**尚未确证（需要一次编辑器空闲窗口）**：三角碎片的直接成因还没钉死——"低模外观"既可能是倒树没走 Nanite 组合，
也可能是回退网格本身。两条可走的检查都要求编辑器空闲：只读体检脚本
（`Tools/Production/inspect_falling_tree_visual.py`，dump 每个变体的组合子部件数与网格、Nanite 设置、材质槽与
Opacity Mask 输入节点）已就绪；运行器 `run_falling_tree_visual_check.ps1` 按项目规则拒绝在他人编辑器占用时另起进程
（"不另起进程覆盖已加载资产"）。当前编辑器内既没有 MCP 服务（`http://127.0.0.1:8000/mcp` 无响应），
也未开启 Python 远程执行，故明确等待用户给窗口。

**下一批（编辑器空闲时一次做完）**：只读体检 → 跑 `fix_harvest_material_usage_flags.py` → 完整构建
（含 `FALLDIAG` 诊断）→ 由用户实测确认三角是否消失、诊断行显示走了哪条路径。