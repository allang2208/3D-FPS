# 倒树三角碎片：全面修复方案（2026-09-26）

针对用户实测反馈「树倒了以后变成了三角形碎片，砍倒后的全程出现」，本方案给出分诊、分批修复、
验证、性能约束与回滚。**当前状态**：批次 0 已完成（离线），批次 1 需要一次编辑器空闲窗口。

---

## 0. 现象与验收标准

**现象**（用户实测截图，2026-09-25 深夜）：砍倒后**全程**如此——

- 倒下的上半段：树冠变成一片片**几米大的平面三角**（纯色浅绿／橄榄／棕，硬直边缘，无叶片贴图、无叶形镂空）；
  树干变成**尖刺状深色乱片**；
- 对照组：背景里**站立的树正常**，**树桩本体正常**，只有**树桩顶面发白**。

**目标（验收判据）**：

| 编号 | 目标 | 判据 |
| --- | --- | --- |
| G1 | 倒下的上半段树冠与站立树一致 | 用户截图里叶片是真实叶片剪影，不出现平面大三角 |
| G2 | 倒树断面显示木纹（不是默认灰） | 截图 + 日志不再出现该材质的 `missing usage flag` 警告 |
| G3 | 树桩切面显示木纹（不是默认灰） | 同上 |
| G4 | 落地尘土／落叶、四段原木、淡出与销毁保持现状 | 不回归（对比现有表现） |
| G5 | 不增加运行时负担 | 无新增 Actor／Tick／Timer／Trace／每帧资源加载；诊断每次倒树一行日志 |

---

## 1. 已确证的事实（含证据）

| # | 事实 | 证据 | 能解释什么 |
| --- | --- | --- | --- |
| F1 | 倒树断面材质 `M_FallingCutEnd` 缺 `used_with_nanite`，游戏里被替换成默认材质 | `Saved/Logs/FPSGAME.log` 用户实测倒下那一秒 `15:22:48`：`missing usage flag Nanite! Default Material will be used in game.` | G2 |
| F2 | 树桩切面材质 `M_TreeCutSurface` 缺 `used_with_instanced_static_meshes`，游戏里被替换成默认材质 | 同一秒日志：`missing usage flag InstancedStaticMeshes!` | G3（截图树桩顶那块发白） |
| F3 | 两个标志从没被设过 | `SourceAssets/HarvestTimber20260913/import_tree_sections.py` 第 18–23 行只设 `two_sided`＋`used_with_skeletal_mesh`；`build_falling_assemblies.py` 第 7 行只补 skeletal | F1/F2 的根因 |
| F4 | 倒树网格 `SK_CutUpper_*` 引用与原树**完全相同**的 13 个 Megaplant 组合子部件，骨架、槽名、Nanite 设置名齐全；材质带真·黑杨贴图 | 离线读 `.uasset` 明文（名称表／导入表） | 排除"子部件丢失／贴图丢失" |
| F5 | 落地特效资产引用齐全（`P_Destruction_Wood`、`FX_FallingLeaves` → `SM_Leaf_01/03` + `MI_Scatter_03`） | 同上 | 排除特效缺资产 |
| F6 | 四变体"倒树/原树"体积比一致（A 33%、B 30%、C 33%、D 32%） | `Content/Items/HarvestTimber` 与 `Content/WorldGeneration/TemperateHills` 文件大小 | 排除"A 变体独有缺陷" |
| F7 | 变体 A 的组合资源**保存成功但报告崩了**，`assemblies.json` 只有 B/C/D（11/14/12） | `Saved/Logs/CutTreeAssemblies-Import.log`：先 `Saving Package: SK_CutUpper_A`，再 `NaniteAssemblyData … 'nodes' is protected` 崩溃 | A 的部件数**从未被验证过** |
| F8 | 截图里的三角是**平面着色多边形**，不是"叶片卡片丢遮罩" | 截图裁切放大 5× 逐块判读：纯色、硬边、无贴图无镂空 | 指向"没有按 Nanite 组合渲染"或"组合子部件变换错位" |

---

## 2. 分诊决策树（先测后改）

体检脚本 `Tools/Production/inspect_falling_tree_visual.py`（只读）与新增的 `FALLDIAG` 日志行一起给判据：

```
FALLDIAG mesh=… nanite_data=? force_disable_nanite=? disallow_nanite=? skinned_nanite_allowed=? lods=? predicted_lod=? slots=[…]
```

| 判据 | 指向 | 走哪条修复 |
| --- | --- | --- |
| `skinned_nanite_allowed=0` | 引擎／项目层面**不允许骨骼网格走 Nanite** | 分支 2B-1（关掉限制）或 2C（保底表现） |
| `nanite_data=0` | 资产 Nanite 数据没落盘 | 分支 2B-2（重制并硬校验） |
| `force_disable_nanite=1` 或 `disallow_nanite=1` | 组件／资产被显式禁用 | 分支 2B-3（去掉禁用） |
| 体检显示某变体组合子部件数 ≠ 源树，或 A 只有 0／异常 | 组合数据缺失或错位 | 分支 2A |
| 子部件数与源树一致、`nanite_data=1`、`skinned_nanite_allowed=1`，但三角仍在 | 组合节点／骨骼映射或几何本身 | 分支 2A（重制＋校验）或 2C |
| `slots` 里出现 `WorldGridMaterial`／默认材质名 | 又是使用标志问题 | 扩到批次 1 的修复脚本再扫一遍 |

**预期**：F1/F2 修好后 G2/G3 直接达成；G1 由 2A／2B／2C 中命中的那一条解决。

---

## 3. 修复批次

### 批次 0 — 已完成（离线，可复核）

1. `Tools/Production/fix_harvest_material_usage_flags.py`：幂等补齐两个材质缺失的使用标志（重编译＋保存）。
2. 加固制作脚本，重走制作不会再退回：
   - `SourceAssets/HarvestTimber20260913/import_tree_sections.py`：按 `fade` 同时设 `used_with_nanite` / `used_with_instanced_static_meshes`；
   - `SourceAssets/HarvestTimber20260913/build_falling_assemblies.py`：给断面材质补 `used_with_nanite`。
3. `Source/FPSGAME/Production/ProductionFallingTree.cpp`：一次性诊断（`fps.Harvest.TreeFallDiag`，默认 1），
   每次倒树打印一行渲染路径；该翻译单元 `/Zs` 语法检查通过（退出码 0，零错误零告警）。
4. 文档与技能参考更新：`Docs/ProductionTreeHealth-20260925.md` 第 8 节、
   `skills/ue5-world-interaction/references/tree-harvest-cut-and-fall.md`。

### 批次 1 — 需要一次编辑器空闲窗口（约 3 分钟，一次跑完）

1. 只读体检：`powershell -NoProfile -File Tools/Production/run_falling_tree_visual_check.ps1`
   （先跑 `SCOPE='fast'`：A 变体＋站立树基线＋材质；需要时再切 `'full'` 查全变体与特效）。
2. 材质标志修复：`Tools/Production/fix_harvest_material_usage_flags.py`（同一个空闲窗口内，走 commandlet）。
3. 完整构建（含 `FALLDIAG`）：`Build.bat FPSGAMEEditor Win64 Development …`（日志落 `Saved/BuildEditor/`）。
4. 产出一张**判据表**：组合子部件数（四变体 vs 源树）、材质槽与使用标志、`OpMask` 输入节点、
   `HasValidNaniteData`、LOD 数。然后按第 2 节决策树选定分支。

### 批次 2A — 组合数据缺失／错位（对应 F7 与"部件数不符"）

- 在 `build_falling_assemblies.py` 里加**硬校验**（失败即 `raise`，不再只写报告）：
  - 目标组合子部件数 == 源树子部件数（逐变体比对，含 A）；
  - 目标 `HasValidNaniteData()` 为真；
  - 目标骨骼数与源树一致；
  - 每条结果写入 `FellingCut/assemblies.json`（含 A，不再被覆盖：改为**合并写入**）。
- 重跑该脚本（只处理 A 也行：`TREE_CUT_AUTHOR_VARIANTS=A`）重制四／一个 `SK_CutUpper_*`。
- **回滚准备**：重制前把现有 `Content/Items/HarvestTimber/SK_CutUpper_*.uasset` 复制到
  `trash/treefall-triangles-20260926/` 并记录散列（按仓库整理规则）。
- 验证：体检脚本复核部件数与 Nanite 数据；用户砍一棵看 G1。

### 批次 2B — Nanite 路径没生效（对应 `FALLDIAG` 的三个布尔）

- **2B-1 `skinned_nanite_allowed=0`**：确认引擎开关
  （`USkinnedMeshComponent::ShouldRenderNaniteSkinnedMeshes()` = `NaniteSkinnedMeshesSupported() && GSkinnedMeshRenderNanite != 0`，
  实现见 `Engine/Source/Runtime/Engine/Private/Components/SkinnedMeshComponent.cpp`）。
  找到对应 CVar 名后：要么在项目侧显式打开（`Config/DefaultEngine.ini`，并如实记录常驻代价），
  要么判定"本机不支持骨骼 Nanite"，转 2C。**不允许**用"看起来还行"当结论。
- **2B-2 `nanite_data=0`**：资产 Nanite 数据没落盘 → 按 2A 的硬校验重制；
  注意制作期 Nanite 构建耗时（A 154 s、B 176 s 量级）属**离线**成本，不代表运行时。
- **2B-3 `force_disable_nanite=1` / `disallow_nanite=1`**：定位是谁设的（组件构造、资产设置、
  `r.SkeletalMeshForceLOD` 之类的调试 CVar），去掉后复测。

### 批次 2C — 保底表现方案（不依赖骨骼 Nanite 组合）

若 2A／2B 都无法让倒树正确渲染组合树冠，改用**站立树已验证可用**的资产做倒树表现：

- 用**原树网格**（站立树渲染正常，已实测）作为倒下的上半段，切口用**材质遮罩**裁掉切口以下
  （即本案例上一代方案 `step(H,P.z)`，`import_tree_sections.py` 第 42–45 行正是把它删掉改成真实断口的地方）；
- 断面真实感下降（回到"材质裁切"而非"封闭断口"），但 G1 优先；
- 若仍要真实断面，可保留 `SM_CutUpper_*` 的断口片贴在上段底部；
- 代价：不倒树时零额外开销（与现状相同）。

### 批次 3 — 验收与定稿

- 用户进游戏砍一棵树并截图（**我不主动 PIE／不主动截图**）；我用会话内 `read_image` 判读并与现截图对比；
- 我复核日志：`FALLDIAG` 一行、无 `missing usage flag` 警告、无新的材质／Nanite 错误；
- 更新 `Docs/ProductionTreeHealth-20260925.md`（结论替代"尚未确证"段）与技能参考；
- 是否需要提交由用户决定（本方案不自动提交）。

---

## 4. 性能约束（用户长期要求）

- 运行时**不新增** Actor、Tick、Timer、Trace、每帧材质参数以外的工作；倒树仍走既有预加载＋一次性生成的路径。
- 新增的 `FALLDIAG` 是**每次倒树一行**日志，确认后可 `fps.Harvest.TreeFallDiag 0` 关闭。
- 2A／2B 的改动都发生在**制作期**（离线 Nanite 构建、材质重编译），不影响运行时帧开销。
- 2C 只是换用已有资产，运行时开销不高于现状。
- 不做、也不建议做：实时切割网格、整树刚体／Chaos 模拟、为倒树加独立渲染组件。

---

## 5. 风险与回滚

| 风险 | 处理 |
| --- | --- |
| 重制 `SK_CutUpper_*` 后更差 | 重制前备份原资产到 `trash/treefall-triangles-20260926/`；失败即还原 |
| 打开骨骼 Nanite 带来常驻代价 | 先在项目配置里显式打开并如实记录；若用户不接受则走 2C |
| 制作脚本重跑覆盖 `assemblies.json` | 批次 2A 改为合并写入，保留历史 |
| 与并行会话的构建互斥冲突 | 按既有做法：构建放后台队列，冲突时保留现场并只在本对话说明，不联系其他对话 |

---

## 6. 明确不做（本轮范围外）

- 不改树木生命值口径、掉落数量、存档字段（含那棵残留 54% 生命的一次性迁移）；
- 不做完整物理破坏／Chaos 倒树、不做实时切网格；
- 不因为本次问题改动站立树的世界材质与 PCG 实例化路径；
- 不主动测试、不主动 PIE、不主动截图验收（用户规则）。

---

## 7. 执行清单

- [x] 批次 0：材质标志修复脚本、制作脚本加固、`FALLDIAG` 诊断、`/Zs` 通过、文档与技能更新
- [x] 批次 1–3：只读体检 + 材质标志修复（**已落盘**）+ 完整构建（含 `FALLDIAG`/`FALLDIAG_ASM`）→ 见第 9 节
- [x] 批次 2C：保底方案核对（上一代材质可用）+ **代码已落地**（`fps.Harvest.TreeFallUseSourceMesh` 默认 1）→ 见第 10 节
- [ ] 批次 2A/2B：仅在保底路径实测不理想时继续追究重制网格的 `Nodes`／骨骼绑定
- [ ] 批次 3：用户实测验收（砍一棵树看树冠、断面、树桩切面）→ 文档定稿 →（按用户意愿）提交

---

## 8. 执行记录与复用陷阱（2026-09-26 00:2x–01:0x）

编辑器于 00:2x 关闭，批次 1 开始执行。**第一次尝试失败，原因不在引擎而在脚本参数写法**，
两条都值得记下来：

1. **`-script=$pyScript` 不会被 PowerShell 5.1 展开**。运行器与批次脚本原本都写成
   `-run=pythonscript -script=$var`，引擎收到**字面量** `$script` 并把它当 Python 代码执行：

   ```
   LogPython: Error: SyntaxError: invalid syntax (<string>, line 1)
   LogPython: Error:   $script
   LogPython: Error:   ^
   ```

   修法：`("-script=" + $路径)` 显式拼接；另外别用 `$script` 这种和 `script:` 作用域前缀同名的变量。
   修好后 `run_falling_tree_visual_check.ps1` 已按此写法，复用时照抄这一行。
2. **用编辑工具改 `.ps1` 会丢掉 UTF-8 BOM**。该项目 `.ps1` 含中文注释，没有 BOM 时 Windows
   PowerShell 5.1 按 ANSI 读，会报 `The string is missing the terminator: "`。本次改完运行器后
   首三字节从 `239,187,191` 变成了 `35,32,230`，已用
   `[IO.File]::WriteAllText($p,$t,[Text.UTF8Encoding]::new($true))` 补回；**每次改完 .ps1 都要复核这三字节**。
3. **并行会话构建期间不要留引擎实例**：commandlet 会加载并锁住
   `Binaries/Win64/UnrealEditor-FPSGAME.dll`，正好挡住并行会话的链接（这也是本会话早先
   "必须等用户关编辑器才能完整构建"的同一原因）。本次发现另一会话在 00:36:51 起构建
   `FPSGAMEEditor`（`cl.exe … FluidPresentationSubsystem.cpp.obj`），按 WORKFLOW 第 7 节
   **先停掉自己的 commandlet、等对方构建结束后再提交自己的构建**，不去抢 `-WaitMutex`。

后续执行改为 `batch2`：等待并行构建结束 → 只读体检（修正后的运行器）→ 材质标志修复 →
再由本任务决定是否需要自己的完整构建（若并行构建已把含 `FALLDIAG` 的
`ProductionFallingTree.cpp` 一起编入并链接成功，则不必重复构建，但要在日志里核对这一点）。

---

## 9. 批次 1–3 执行结果与分诊结论（2026-09-26 00:2x–01:0x）

### 9.1 已确证并已修复（G2/G3）

| 项 | 修复前 | 修复后 | 证据 |
| --- | --- | --- | --- |
| `/Game/Items/HarvestTimber/M_FallingCutEnd`（倒树断面） | `used_with_skeletal_mesh=True`、**`used_with_nanite=False`** | 两个都为 True，**已保存落盘** | `batch3-flagfix-20260926-005615.log`：`HARVESTFLAG_DONE checked=2 changed=2`；资产 SHA256 由 `1A9985…` 变为 `D07D18…` |
| `/Game/Items/HarvestTimber/M_TreeCutSurface`（树桩切面） | **全部使用标志 False** | `used_with_instanced_static_meshes=True`，已落盘 | 同上；SHA256 由 `CCCD9E…` 变为 `38DAE9…` |

无头 commandlet 里 `recompile_material` 一定返回假（没有着色器编译环境），**不能当成失败**
（先前那版直接 `raise`，导致资产都没保存）。已改为记录 `HARVESTFLAG_RECOMPILE_DEFERRED` 后继续保存；
着色器映射在编辑器或游戏加载该资产时重建。

### 9.2 用证据排除的原因（这些都不是三角碎片的成因）

| 假设 | 实测 | 结论 |
| --- | --- | --- |
| 变体 A 的组合数据丢失（历史上 A 的统计崩过） | `SK_CutUpper_A` 与源树 `SK_BlackPoplarPCG_A` 均为 `parts=13` | **排除**，A 的组合部件完整 |
| 倒树还留着原树的经典 LOD，非 Nanite 路径画出未切的原树代理 | 倒树 `lod0_verts=12120 / lod_count=1`，源树 `15543 / lod_count=1` | **排除**：倒树只有 LOD0 且是纯树干几何（无树叶），经典路径**画不出树冠**——所以那些大叶片**只能来自 Nanite 组合** |
| 叶片材质/遮罩不对（叶片退化成实心卡片） | 倒树材质调用 `MF_TwoSided_Leaves` + `MF_DefaultLit_Trunk`，与站立树 `M_BlackPoplarPCG` **完全相同**；`MI_CutUpper_Foliage` 的贴图（`T_Black_Poplar_01_Foliage_CA/NT`）、静态开关、颜色与 `MI_BlackPoplarPCG_Foliage` **逐项一致**，只多了 `Harvest*` 参数 | **排除**，材质链正常 |
| 位移（WPO）把叶片拉爆 | 弯曲自定义节点 `Bend*pow(saturate((P.z-42)/max(Height-42,1)),2)`，`CrownBend` 上限 ±55（cm 量级），对单张叶片卡片的差动只有几厘米 | **降级**，不足以造成米级平板 |

**截图判读（放大对比，最终依据）**：站立树树冠是细小、有纹理层次的叶片；倒下的树冠是**几米大的平板
多边形**（绿、棕都有、硬边、无纹理）——**整块网格一起变形**，不是遮罩或材质问题。

### 9.3 新的主嫌疑：Nanite 组合的 `Nodes`（部件摆位数据）

`Engine/Classes/Engine/NaniteAssemblyData.h`：

```cpp
struct FNaniteAssemblyNode { int32 PartIndex; ENaniteAssemblyNodeTransformSpace TransformSpace;
                             FTransform3f Transform; TArray<FNaniteAssemblyBoneInfluence> BoneInfluences; };
struct FNaniteAssemblyData { TArray<FNaniteAssemblyPart> Parts; TArray<FNaniteAssemblyNode> Nodes;
                             bool IsValid() const { return Parts.Num() > 0 && Nodes.Num() > 0; } };
```

- **`Parts` 只说明"用了哪些网格"，`Nodes` 才决定"每个部件摆在哪、绑到哪根骨头"**；
- python 只能读 `Parts`（`Nodes` 是受保护属性，历史上读它还把 A 变体的统计批次打断过），
  所以"13/13 一致"**不能证明部件摆位正确**；
- 重制流程（`build_falling_assemblies.py`：`duplicate_asset` → 写 LOD0 几何 →
  `apply_nanite_settings` 复制源设置 → `REMAP_GEOMETRY_TO_REFERENCE_SKELETON`）
  里任何一步丢掉或改写 `Nodes`／骨骼绑定，表现就是**所有部件塌到原点附近互相重叠**——
  正是截图里"树干附近一团几米大的平板"。

**为此新增 C++ 诊断**（`fps.Harvest.TreeFallDiag`，默认开，每次倒树一行，O(节点数)）：

```
FALLDIAG_ASM falling mesh=… parts=… nodes=… valid=… bones=… bone_relative=… no_influence=… bad_bone=… max_node_translation=…
FALLDIAG_ASM source  mesh=… parts=… nodes=… valid=… bones=… …（同一行的源树对照，FindObject 取，不触发加载）
```

判读：`nodes=0`／`valid=0`／`no_influence>0`／`bad_bone>0`／`max_node_translation` 比源树大一个
数量级 ⇒ 组合摆位数据在重制时丢了或错了；两棵树统计一致 ⇒ 嫌疑转到几何本身的蒙皮/绑定。

### 9.4 保底方案（2C）已确认可用材料

上一代"原树网格 + 材质遮罩裁切"的材质仍在：`M_FallingPoplar`、`MI_FallingPoplar_Bark`、
`MI_FallingPoplar_Foliage`（2026-09-13 20:22，即重制之前那一代）。
`Tools/Production/inspect_falling_legacy_materials.py` 正在核对它们是否带切口遮罩与 `Harvest*` 参数；
若可用，2C 就是"把倒树上半段换回**站立树已验证可渲染**的原树网格 + 这套材质"，
完全绕开重制几何与组合摆位，代价是断口真实感下降。

**核对结果：可用，而且参数完全对接**（`Tools/Production/inspect_falling_legacy_materials.py`，日志
`Saved/ProductionTreeHealth/legacy-materials-20260926-010312.log`）：

- `M_FallingPoplar`：`used_with_skeletal_mesh / instanced_skinned / instanced_static / nanite` **全为 True**，
  `BLEND_MASKED`、`two_sided`、`dithered_lod_transition`，不透明遮罩自定义节点为
  **`return O*step(H,P.z)*step(frac(sin(...)),F);`** —— 正是"裁掉切口以下 + 抖动淡出"；
- 参数名 `HarvestCutHeight / HarvestTreeHeight / HarvestCrownBend / HarvestFade` 与 `ProductionFallingTree.cpp`
  现有设置**逐一对应**，无需改参数口径；
- 它的两个实例 `MI_FallingPoplar_Bark / MI_FallingPoplar_Foliage` 贴图（`T_Black_Poplar_01_Bark_C/NAH`、
  `T_Black_Poplar_01_Foliage_CA/NT`）与静态开关同现用实例一致。

---

## 10. 已落地的修复（2026-09-26 01:1x）

### 10.1 代码改动

| 文件 | 改动 |
| --- | --- |
| `Source/FPSGAME/Production/ProductionFallingTree.cpp` | 新增 CVar `fps.Harvest.TreeFallUseSourceMesh`（**默认 1**）：倒树上半段改用 `Resource.Mesh` 指向的**原树网格**（站立树正在用的同一份资产，场景里已加载，零额外加载），失败才回退到重制的 `SK_CutUpper_*`；走原树时把槽 0/1 的材质换成 `FallingMaterial(0/1)`（带 `step(H,P.z)` 切口遮罩），`Harvest*` 参数照旧设置；`FALLDIAG` 增加 `FALLDIAG_ASM falling / source / authored` 三行组合节点统计（`parts/nodes/valid/bones/bone_relative/no_influence/bad_bone/max_node_translation`），全部用 `FindObject` 取已加载资产，不触发同步加载 |
| `Source/FPSGAME/Production/ProductionHarvestAssets.cpp` | `FallingMaterial(0/1)` 改指 `MI_FallingPoplar_Bark / MI_FallingPoplar_Foliage`（槽 2 仍是断面材质，供对照路径）；预加载集合补上 `MI_CutUpper_Bark/Foliage`，两条路径都预热 |

两个翻译单元 `/Zs` 语法检查通过（退出码 0，零错误零告警）。

**构建状态（2026-09-26 01:05，如实记录）**：完整构建跑到 `[10/26] Compile ProductionFallingTree.cpp`、
`[15/26] Compile ProductionHarvestAssets.cpp` **两个文件都编译成功、零错误**，随后整轮被**并行会话正在写
的水面文件**挡住而失败（`Source/FPSGAME/Water/ClearwaterWater.cpp` 找不到
`WorldGeneration/RiverPilotFXSubsystem.h`；`Source/FPSGAME/WorldGeneration/ClearwaterWaterFootprint.cpp`
把 `FBoxSphereBounds` 当 `TBox<double>` 用）。按项目规则不代改他人文件、不联系其他会话，已挂后台重试构建
（先等对方构建让出、失败则间隔重试，成功即停）。因此：

- 当前 `Binaries/Win64/UnrealEditor-FPSGAME.dll`（01:02:19）**含** `FALLDIAG`/`FALLDIAG_ASM` 诊断，
  **不含**本文第 10.1 节的保底修复（链接还没成功）；
- 保底修复一旦链接成功，用 `FALLDIAG` 那一行核对即可（`mesh=` 应显示 `SK_BlackPoplarPCG_x`）。

**重试结果（01:05–01:23）**：连续 10 次构建全部因同一批并行会话文件失败，卡点始终是
`Water/ClearwaterWater.cpp`（缺 `WorldGeneration/RiverPilotFXSubsystem.h`）、
`WorldGeneration/ClearwaterWaterFootprint.cpp`（`FBoxSphereBounds` 当 `TBox<double>` 用）、
`WorldGeneration/GrassDeform/GrassFootstepFeedbackComponent.cpp`（`DecalFadeParameter` 未声明、
`UDecalComponent` 无 `SetCastShadow`/`bReceivesDecals`）。已改为**按源码改动触发**的稀疏重试
（源码 6 分钟内无人改动就跳过，避免空转），成功即自动核对 DLL。

**验证方法修正**：先前的 DLL 字符串检查只比对了 3 个字节（漏掉 `+2`），可能误报；已改为逐字节严格
UTF-16 比对。修正后结论与先前汇报一致：DLL 含 `FALLDIAG_ASM`、不含 `TreeFallUseSourceMesh`。

**最终结果（01:26:41）**：并行会话修好其水面/草地文件后，按源码改动触发的重试在第 2 次尝试即成功
（`[9/11] Link UnrealEditor-FPSGAME.lib` → `[10/11] Link UnrealEditor-FPSGAME.dll` → `Result: Succeeded`，
日志 `Saved/BuildEditor/build-treefall-20260926-012349-a2.log`）。严格核对
`Binaries/Win64/UnrealEditor-FPSGAME.dll`（13,895,168 字节，01:26:40）：

| 字符串 | 含义 | 结果 |
| --- | --- | --- |
| `TreeFallUseSourceMesh` | 保底开关（本次新增代码） | **在** |
| `FALLDIAG_ASM` | 组合节点统计诊断 | 在 |
| `MI_FallingPoplar_Bark` | 上一代带 `step(H,P.z)` 遮罩的材质引用 | **在** |

即：**诊断与保底修复都已进入编辑器 DLL**，用户下次启动编辑器砍树即生效
（`FALLDIAG` 的 `mesh=` 应为 `SK_BlackPoplarPCG_x`）。运行时表现尚未验证——按用户规则由用户实测。

### 10.2 为什么这样最稳

- 画面里的站立树用的就是这份网格与这套叶片材质，**渲染正确已被实际画面证明**；重制路径唯一多出来的
  就是"切开树干 + 换 Nanite 组合摆位"，也正是坏掉的那一步——绕开它就绕开了全部不确定性；
- 切口改由材质 `step(H,P.z)` 遮掉切口以下，配合同一次操作已生成的树桩遮挡根部，是上一代已验证的做法；
- 想要 A/B 对照时控制台执行 `fps.Harvest.TreeFallUseSourceMesh 0` 即可切回重制版，**不需要重新构建**。

### 10.3 性能

- 不新增 Actor/Tick/Timer/Trace/每帧查询；网格用已加载资产，材质换成本就更小的两个实例；
- 诊断仍是每次倒树固定几行、O(节点数) 的只读统计，`fps.Harvest.TreeFallDiag 0` 可关；
- 预加载只多了两个几十 KB 的材质实例。

### 10.4 仍未验证的部分（如实声明）

- **没有运行 PIE、没有截图、没有验收**（按用户规则由用户实测）；本轮的判据是资产体检、日志与编译；
- 重制路径 `SK_CutUpper_*` 的组合摆位缺陷**尚未用 `FALLDIAG_ASM` 实测确认**（需要一次真实倒树：
  走保底时 `authored` 行只有在该网格被加载时才会打印，把 CVar 设 0 再倒一棵即可拿到对照）；
- 上一代材质 `M_PoplarEnd` 的使用标志仍全为 False（当前倒树路径不使用它，未动；若将来用它做断面需补标志）。

---

## 11. 断口闭合：用户第二次反馈（2026-09-26 12:2x）

用户实测反馈：**"树桩切面处理好了，但树倒下的阶段面是中空的"**。这是保底路径的固有缺口——原树干是
**空心筒**，材质 `step(H,P.z)` 只把切口以下裁掉，断口就露出筒内；重制网格本来带真实封盖（材质槽
`CutEndGrain` / `M_FallingCutEnd`），但重制路径已因树冠问题弃用。

### 11.1 做法：把真实封盖面单独提取出来

新增 `Tools/Production/build_tree_cut_caps.py`，**在编辑器内通过 MCP 桥运行**（避免另起进程写资产）：
`SM_CutUpper_<A..D>` → DynamicMesh → 按材质号统计 → `delete_triangles_by_material_id` 删掉树皮（槽 0）
→ `remap_material_i_ds` 归到槽 0 → `create_new_static_mesh_asset_from_mesh` 生成 `SM_CutCap_<A..D>`
→ 槽材质设为 `M_FallingCutEnd`。只读源网格、只新建封盖资产。由
`Tools/Production/verify_tree_cut_caps.py` 只读复核：

| 变体 | 源网格三角形 | 封盖三角形 | 槽 | 封盖 Z 中心 | 封盖直径 (X×Y) |
| --- | --- | --- | --- | --- | --- |
| A | 338,474 | 388 | `Material_0 = M_FallingCutEnd` | 42.0 | 78 × 79 cm |
| B | 774,251 | 388 | 同上 | 42.0 | 78 × 79 cm |
| C | 621,310 | 560 | 同上 | 42.0 | 52 × 52 cm |
| D | 514,617 | 378 | 同上 | 42.0 | 27 × 27 cm |

关键点（直接决定接入方式）：**封盖顶点就保存在树本地坐标**（Z 中心 42.0 = 切口平面，`extent.z = 0`
完全平坦）→ 组件挂到 `Tree` 下**不需要任何偏移**；`M_FallingCutEnd` 带切面烘焙 UV、`two_sided`、
`BLEND_MASKED`、`HarvestFade` → 封盖能跟树干一起抖动淡出。

### 11.2 接入

| 位置 | 改动 |
| --- | --- |
| `ProductionFallingTree.h/.cpp` | 新增 `CutCap`（`UStaticMeshComponent`）：构造函数挂到 `Tree` 下，**不碰撞、不导航、不 Tick、不投影**（在筒内），默认隐藏；`InitializeFall` 仅在走原树网格（材质遮罩）时挂封盖 + MID（写 `HarvestCutHeight`/`HarvestTreeHeight`/`HarvestFade`）并加入 `Materials`，与树干同步淡出；`Tree` 隐藏时靠 `bPropagateToChildren` 连带隐藏（Tick 不用改）。走重制路径时清空封盖（它自带真实断口） |
| `ProductionHarvestAssets.h/.cpp` | 新增 `CutCap(Variant)` 路径函数并加入 `LoadSet` 预加载（4 片几十 KB 小网格） |
| `FALLDIAG` 行 | 追加 `cap=<网格名>`，运行时可确认封盖是否挂上 |

### 11.3 本轮踩到的两个执行陷阱（已写入技能）

1. **新增 `UPROPERTY` 后不能用 `/Zs` 验证**：UHT 输出（`*.generated.h`）还是旧的，而 `/Zs` 不跑 UHT，
   于是报出 `UCLASS`/`GENERATED_BODY()` "宏未展开、缺少类型说明符"这类**假错误**（本轮实际被误导一次）。
   真实判据是真跑一次 UHT+编译：日志里出现 `Compile [x64] <文件>.cpp` 且无 `error C` 才算过。
2. **PowerShell 里 `$x = Invoke-Build ...` 会吞掉函数内所有 `Write-Output`**（返回值变数组、条件判断失真）；
   驱动脚本函数内改用 `Write-Host`，或把结果写文件后再判断。

### 11.4 状态

- ✅ 四片封盖资产已生成并只读复核通过（编辑器内完成，未另起进程、未覆盖已加载资产）；
- ✅ C++ 已通过**真实 UHT+编译**（`[16/22] ProductionFallingTree.cpp`、`[17/22] ProductionHarvestAssets.cpp` 零错误；
  随后整轮 `[1/11]`…`[6/11]` 全模块编译也零错误）；
- ✅ **链接成功（12:45:21）**：`[12/14] Link UnrealEditor-FPSGAME.lib` → `[13/14] Link UnrealEditor-FPSGAME.dll`
  → `Result: Succeeded`，日志 `Saved/BuildEditor/build-cutcap-20260926-124458-a1.log`。严格逐字节核对
  `Binaries/Win64/UnrealEditor-FPSGAME.dll`（13,989,376 字节，12:45:21）：

  | 字符串 | 含义 | 结果 |
  | --- | --- | --- |
  | `CutFaceCap` | 断口封盖组件（本次新增） | **在** |
  | `SM_CutCap_` | 封盖资产引用 | **在** |
  | `TreeFallUseSourceMesh` | 树冠保底开关 | 在 |
  | `FALLDIAG_ASM` | 组合节点统计诊断 | 在 |

- ✅ 偏移正确性已核对：`ProductionTreeFallPlan.h` 里 `static constexpr float CutHeight=42.f` 是**编译期常量**，
  与封盖烘焙的 Z=42 一致 ⇒ 组件挂 `Tree` 下**零偏移**就是贴合的（若将来改 CutHeight 常量，封盖资产要重跑
  `build_tree_cut_caps.py` 并在需要时按下式补偿：`偏移 = CutHeight - 封盖包围盒 Z 中心`）；
- ⏳ 断口是否真的闭合**未验证**，按用户规则由用户实测（实测时 `FALLDIAG` 行应出现 `cap=SM_CutCap_x`）。

---

## 12. 取消截断：用户第三次反馈（2026-09-26 12:5x）

用户实测：**"截断部分虽然闭合，但从截断部分向外延展的树皮还是突出来没有去除……原来设计应该是树木原模型
倒下，没有做截断处理"**。

### 12.1 成因

保底路径把材质遮罩的 `HarvestCutHeight` 设成了 `Plan.CutHeight = 42`，于是只隐藏 `P.z < 42` 的部分。
但原树模型在切口高度附近还有**向外张开的根部树皮（板根）**，它的高度会超过 42 cm——这部分留在原地，
看起来就是"从截断面往外支棱出来的树皮"；封盖直径按树干横截面取（A/B 约 78 cm），盖不住更宽的板根。

### 12.2 修法（按用户说明的原设计：整棵原树直接倒，不做截断）

| 位置 | 改动 |
| --- | --- |
| `ProductionFallingTree.cpp` | 新增 CVar `fps.Harvest.TreeFallCutAtStump`（**默认 0＝不截断**）。遮罩高度改为 `bCutAtStump ? Plan.CutHeight : -1000`：`step(H,P.z)` 在 `H` 低于模型最低点后恒为 1，等于完全不裁；断口封盖也只在 `bCutAtStump` 时才挂（不截断就不需要，重制网格自带真实断口也不受影响）。`FALLDIAG` 追加 `cut_at_stump=` |

- 树仍然用**站立树原网格**（树冠已验证 ✓）、仍用 `M_FallingPoplar` 系材质——因为需要它的 `HarvestFade`
  抖动淡出；材质函数、贴图与静态开关与站立树逐项一致（第 9.2 节已验证），只是把切口遮罩关掉，
  等价于"原树材质 + 淡出"。
- 树桩仍是同一次操作生成的那一个，位置不变；整棵树从地面倒下去，根部与树桩/地面自然交叠。
- 想对照旧的"42 cm 截断 + 封盖"表现：控制台 `fps.Harvest.TreeFallCutAtStump 1`（无需重新构建）。

### 12.3 可能的后继项（未验证，等实测）

整棵树倒时，`Z≈0` 处树干底口会随根部抬起而可能露出筒内（原树网格底部是否封闭尚未确认）。若实测看到
底口中空，用同一套办法即可闭合：`SM_CutCap_*` 仍然保留，把组件偏移改成 `-Plan.CutHeight`（即贴到
`Z=0`）即可；若底口比封盖更宽，则需按 `Z=0` 轮廓再提取一片更宽的底盖。