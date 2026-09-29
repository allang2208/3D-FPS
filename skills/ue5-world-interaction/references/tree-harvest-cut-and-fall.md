# 树木采集：真实切口、树桩与受控倾倒

适用于可采集树木的模型预处理和倒树接入。资料来自 FPSGAME 2026-09-13 的实现；原生构建与资源制作完成，切口倾倒没有进行游戏或性能验收。按用户当前授权执行测试，不因读取本文件自动启动 PIE 或渲染。

## 当前状态（2026-09-29，用户第五轮反馈后的最终取舍）

- **默认倒树＝几何真切断**：`fps.Harvest.TreeFallUseSourceMesh` 默认 0——倒下的是重制网格
  `SK_CutUpper_*`（42 cm 以上的上半段，自带年轮断面封盖），树桩原地保留；"倒下的就是被锯下的
  那一段"。2026-09-29 的 `FALLDIAG_ASM` 实测推翻了 09-25"重制网格组合数据丢失"的假设
  （SK_CutUpper 与源树 parts/nodes/bones/平移量逐项一致），09-26 技能旧文里"重制资产不可用"的
  结论作废；若 09-25 的树冠塌三角复现（成因未明），CVar=1 一键退回"原树网格+材质遮罩"路径。
- **板根裙边（切口上方外张树皮）**：几何路径由 `M_CutUpperMotion` 淡出遮罩的径向裁剪裁掉
  （`O*saturate(step(T,P.z)+step(length(P.xy),R))*step(噪声,F)`，参数 `HarvestCutRadius` 默认 1e5/
  `HarvestFlareTop` 默认 0＝不裁；C++ 按变体传表 `CutClampRadiusCm={40.0,39.8,26.3,13.9}`、
  `FlareBandTopCm={90,90,62,90}`，C 丛生形只裁到 62）。`M_FallingPoplar`（对照路径用）已恢复
  出厂原状、不含裁剪参数——设参为无害空操作。
- **材质图编辑铁律（09-28 事故教训）**：commandlet 里 `set_editor_property('inputs',...)` 原始
  数组写入 + 后续活编辑器 reconcile 会把材质图**清空**（EXPR_COUNT 0）。材质图编辑只允许在
  活编辑器短批次内完成，且 connect 必须查返回值（返回 bool 不抛异常）、recompile 看返回的
  错误数组（空＝成功，bool(空数组) 是 False 别误读）、保存前后做表达式计数守卫。回退备份在
  `trash/treefall-restore-20260928/`（M_FallingPoplar SHA c4880864…、M_CutUpperMotion SHA c2f06285…）。
- 树桩切面 `M_TreeCutSurface` 与断面 `M_FallingCutEnd` 均接年轮贴图 `T_PoplarEndReference`；
  使用标志修复（2026-09-26）保留。`fps.Harvest.TreeFallCutAtStump 0` 保留整树倒伏对照。
- **活编辑器自检截图（2026-09-29，三项全过）**：`Tools/Production/selfcheck_geocut_visual.py`
  在 500 m 高空 spawn 倒树段+自配光照，SceneCapture2D 逐帧采集三相位读图判定——A=断面年轮封口
  （浅木色切面+同心环）✓、B=板根裁剪对照（关裁剪可见裙边外扩、开裁剪轮廓干净）✓、C=树冠密集
  小叶片无塌三角✓。详见 `Docs/TreeCutNaturalSever-20260928.md` §5.4。
- **截图工具链坑**：Python `Rotator` 顺序是 (roll, pitch, yaw)；编辑器 spawn 的 SceneCapture2D
  根组件要设 MOVABLE，且 `set_actor_location/rotation` Python 无默认参必抛 TypeError、异常被
  Slate 回调吞掉（症状：相机停在出生位、每相位导出同构图）——传全参 + 全体回调 try/except 落日志。
- **瞬态 actor 泄漏会进地图文件**（2026-09-29 事故）：崩溃于 cleanup 之前的工具运行留下的
  transient actor 被后续地图保存烤进 `DayNight_Lighting.umap`（28 个，含 9 个方向光）。spawn
  瞬态 actor 的脚本必须开头先清扫残留、结束 destroy；多会话环境下"我不保存就没事"不成立。
- **第六轮"倒木一根突出物"＝内壁舌头**（2026-09-29 已修）：SK_CutUpper 树干是双层壳（外皮
  r30-46 + 内壁 r15-30），内壁层在个别方位扇区下垂到切口附近、该扇区外皮又稀疏——内壁从缺口
  露出＝倒木上"光滑发黑细杆"。定位法＝commandlet 只读按"方位角扇区×半径带"统计顶点簇
  （`probe_stub_sectors.py`）；分带最大半径看不见它（细簇不抬最大值）。修法＝M_CutUpperMotion
  Custom 加 `(60<z<ZMax)∧(yaw 窗 Y±W 环形回绕)∧(r<31)` 掩码，C++ 按变体传表
  `StubYawDeg/TolDeg/ZMaxCm`（C 丛生形禁用）。60 以下不碰＝年轮断面无损；r<31＝不伤外皮。
- **Custom 节点脚位名必须等于代码里的标识符（短名）**：脚位写参数全名（HarvestStubZMax）而
  代码引用 `Z` → recompile 报 undeclared identifier ×24。脚位/参数分两套名字管理；改完脚位
  后 `connect_material_expressions` 按**脚位名**连。
- **编辑器自动化三坑（2026-09-29）**：① `-unattended` 编辑器里 actor 变换疑似不生效（截图
  相机永远停在出生位、导出同构图），要 spawn/截图的自动化编辑器**去掉该参数**；② uasset 保存
  被并行编辑器的内存映射挡住（`save_loaded_asset`/`save_dirty_packages` 返回 False 且文件
  mtime 不动），关掉多余编辑器即好；③ 隐藏编辑器会被外部守护清场，编辑器内作业要走
  "拉起→等就绪→干活→自杀"一条龙（`Tools/Production/auto_orbit.ps1` 模板，就绪探针
  `probe_asset_ready.py`）。MCP 会话被并发桥调用搞坏后用 `-NewSession` 重握手。
- **DLL 里找 TEXT() 字面量要用 UTF-16 搜索**：ASCII grep 判"没编进去"是误判。
- 完整方案与实测数据见 `Docs/TreeCutNaturalSever-20260928.md`。验收状态按用户规则由用户拍板。

## 先区分主干几何与组合树冠

- Nanite 骨骼树的普通 FBX 可能导出简化 fallback，根部会缺失。需要保留原树树桩时，从 Geometry Script 的 `SOURCE_MODEL` 取得主干源几何，保留局部原点、单位、UV 和自定义法线。
- `SOURCE_MODEL` 也不等于完整树冠。UE 5.8 Nanite Assembly 的叶片、枝条可能来自独立子资产；主干只有树皮面、材质表却包含叶片槽，并不一定是材质 ID 丢失。先读源资产的组合配置。
- 此类树的可行路线：离线切开主干，再复制原骨骼树资产，仅替换主干源几何，保留骨架、Nanite Assembly 节点、子资产引用和材质映射。不要把只有主干的静态 FBX 当作完整倒树模型。
- 倒树"变成大三角碎片"要按形态分诊：**平面着色的多边形**（纯色、硬直边缘、没有叶片贴图与叶形镂空）是低模／代理几何，说明该网格没有按 Nanite 组合渲染（组件或材质的使用标志、Nanite 数据、经典 LOD 各自都要查）；**带贴图但镂空失效的卡片**才是叶片遮罩（Opacity Mask）没生效。两者改的地方完全不同，别混。
- 向静态/骨骼资产复制 DynamicMesh 时显式提供材料表；创建时默认材料槽数不足可能压缩面材质 ID。导入 FBX 也可能删除未使用槽，按名称识别后重映射，不能假定导入后的第 1 槽仍是叶片。
- 原树的叶片组合若映射到槽 1，新增断面应另占槽，保留原映射；FPSGAME 当前约定树皮 0、叶片 1、断面 2。这是本案例配置，不是所有树的通用顺序。

## 同一切平面产生匹配的上下段

- 由同一源主干、同一局部切平面生成下段树桩与上段，分别沿真实边界封面。切割高度按树形配置；本案例局部 Z=42 cm 不是新树的固定标准。
- 下段保留原始根部；上段几何实际去掉切口以下部分。真实切开后移除旧的材质根部裁切，避免把切口封面也遮掉。封面 UV、实心原木的制作细节见 `ue5-item-asset-workflow` 的 `references/solid-timber-and-cut-surfaces.md`。
- 保存导入 UE 后的切口轮廓，统一为局部厘米坐标，避免 FBX 轴/单位转换导致模型与支点错位。
- 倾倒方向转回树的局部坐标，在轮廓上选择前缘支点。更新世界旋转时同步修正位置：`位置 = 世界支点 - 旋转(局部支点 × 缩放)`。前缘留在原位，后缘向上抬起，避免围绕切口中心转动造成下缘穿入树桩。

## 采集事务与显示时序

- 树木像怪物一样有生命值（2026-09-25 用户要求）：上限按树种与实例尺寸取，斧头按**伐木伤害**扣血，
  剩余生命 ≤ 0 的那一挥才倒。此前每一挥只提交生命进度，不产材料、不倒树。
- 口径唯一入口是 `Production/ProductionTreeHealth.h`：生命表、尺寸系数、挥砍伤害（＝自卫伤害面板 ×
  「所需有效命中」改造折算）与 `fps.Harvest.TreeHealthScale` 都在那里，浮窗、图鉴、提示栏与结算
  都读它，不各自换算。
- 存档只存**剩余生命比例**（`FColdSteelProfile::TreeHealth`，键同资源 ID）：调生命上限不改旧档含义，
  旧档仅有累计命中时按 `1 − 命中/3` 读一次即等价，不做迁移遍历。采尽仍补写命中数并登记 `TreeGrowth`，
  世界的采尽判定、树桩重建与 PCG 补生继续按命中数口径工作。
- **树桩可劈（2026-09-28 用户要求）**：桩是独立采集目标——生命＝树立满生命×0.5
  （`ProductionTreeHealth::StumpMaxHealth`），比例存 `FColdSteelTreeGrowth::StumpHealthRatio`；
  采集子系统给 64 m 内每个未劈的桩挂隐形矮碰撞盒（组件打 `HarvestStump` 标签，与树桩渲染同表
  同节拍重建），`ResolveProductionResource` 按 ≤5 cm 位置反查解析成 `bStump` 资源；`CommitStumpStrike`
  扣血，劈尽掉 1 块木材（绕桩散落）、`bStumpCleared=true`、桩与碰撞随脏标记消失。桩不受"幼树
  生长中"门禁限制。**桩不再随幼树长大自动缩没**（`TreeStumpScale`＝未劈 1/已劈 0）。
- **幼树偏移再生（2026-09-28 用户要求）**：砍倒时 `RegisterTreeGrowth` 把桩留在被砍树当时的位置
  （旧 `SaplingOffset`→新 `StumpOffset`），下一棵幼树在候选点基点附近随机偏移（半径 2.8–6.5 m，
  `FRandomStream(CandidateId+Generation)` 播种，最多重掷 5 次避河岸/陡坡/世界边缘）；扎根高度按
  偏移处地形取。`GetHarvestedStumps/GetRegrowingTrees` 枚举各扩一格、入盒与扎根都用偏移后位置。
  每个候选点同一时间只有一个桩：上一代没劈的桩在新一代被砍倒时被替换。方案与改动清单见
  `Docs/StumpHarvestOffsetRegrow-20260928.md`。
- 树不吃暴击与浮动，提示栏「还需 N 挥」即真实挥砍数；不给树加 Actor、Tick、血条控件或每帧查询，
  瞄准提示仍走原有 0.15 s 刷新。
- 最后一击成功提交采集消耗和奖励后，在同一次游戏线程操作中先显示固定树桩，再移除站立树、生成上半段。不能等倒树完成，或只设置脏标记等待流送定时器，才显示树桩。
- 树桩从稳定资源 ID 和已采集记录重建，保留原位置、旋转和缩放。视觉替换不改变采集次数、掉落数量或旧存档身份。
- 让落地位置、上半段运动、掉落释放共享同一倾倒计划。一次性采样地形，分别估计树冠先接触和主干最终支撑位置；避免每帧遍历整棵树进行射线查询。
- 树冠惯性、落地回弹和渐隐属于表现层；真实伤害、建筑碰撞或网络同步需要各自明确接入，不能将受控倾倒称为完整物理破坏模拟。

## 预算与新增树种

- 从前几次有效挥砍开始异步预加载当前树形。最终提交前确认必要资源就绪，避免先扣除资源却无法生成倒树。倒树组件持有网格后释放预加载句柄。
- 常驻小型树桩/材质与大型上半段分别管理；树桩实例化，地面拾取物按距离、数量和创建频率限流。不要为了省开销抹掉原树冠或破坏采集碰撞。
- 切割、封面、Nanite 构建在制作阶段完成。离线 Nanite 简化耗时几分钟不等于运行时会卡几分钟，也不能反过来当作运行流畅的证据。
- 新模型需要一次预处理，同模型不同实例无需重复制作。普通静态树与 Nanite 骨骼组合树需要不同适配分支。
- 当前 FPSGAME 脚本及 `ProductionHarvestAssets` 仍固定四种杨树 A–D，尚非通用一键工具。扩展时优先以树种配置记录源资产、切高、材料和输出引用，再将现有操作参数化；不要声称配置表已完成。

## UE 5.8 本机操作注意

- Python 可复制整个 `nanite_settings` 以保留组合数据；`NaniteAssemblyData.Nodes` 是受保护属性，读取它作为附带统计曾在资源保存后中断后续批次。不要让不可读的统计字段成为导入前置条件。
- **组合部件"摆在哪"由 `Nodes` 决定，不是 `Parts`**：`FNaniteAssemblyNode` 存 `TransformSpace`（Local／BoneRelative）、`Transform` 和 `BoneInfluences`（`BoneIndex`+`BoneWeight`），`FNaniteAssemblyData::IsValid()` 要求 `Parts` 与 `Nodes` **都非空**。因此"python 读到 `parts=13/13 与源树一致"**不能证明摆位正确**；重制网格（复制资产 → 写 LOD0 几何 → 复制 nanite_settings）后若部件全部塌到原点互相重叠，先怀疑 `Nodes`／骨骼绑定在这一步丢了或被改写了。这段只能从 C++ 读：`Mesh->GetNaniteSettings().NaniteAssemblyData`，核对 `Nodes.Num()`、`BoneInfluences.Num()`、`BoneIndex` 是否在 `GetRefSkeleton().GetNum()` 范围内、以及节点平移量是否与源树同量级（2026-09-26 加的 `FALLDIAG_ASM` 就是这条对照）。
- 判断"倒下后树冠变成大平板"要先把几何与材质分开：若网格只有 LOD0 且顶点数是树干量级（无叶片几何），经典渲染路径就**不可能**画出树冠，那些大叶片只能来自 Nanite 组合；同时若倒树材质调用的材质函数与站立树相同（例如 `MF_TwoSided_Leaves` + `MF_DefaultLit_Trunk`）、实例贴图与静态开关逐项一致，就可以把材质排除。
- **保底路线：重制组合网格一旦摆位坏了，就回到"原树网格 + 材质空间裁切"**。做法是把倒下的上半段换成站立树正在用的**同一份原树网格**（画面里已加载，零额外加载，骨架/蒙皮/组合全部已验证），切口交给带 `step(H,P.z)` 的材质遮罩（FPSGAME 里是 `M_FallingPoplar` 及其两个实例，`HarvestCutHeight/HarvestTreeHeight/HarvestCrownBend/HarvestFade` 参数名与倒树代码一致，可直接对接），根部由同一次操作生成的树桩遮挡。代价是断口没有真实封面；换来的是树冠渲染立刻正确。把它做成 CVar 开关（FPSGAME：`fps.Harvest.TreeFallUseSourceMesh`，默认走保底），需要对照重制版时不用重新构建。
- **默认不要给倒树做截断**（FPSGAME 2026-09-26 用户明确的原设计）：倒下的应当是**整棵原树模型**，不在树桩高度处平面截断。原因很实际——原树在切口高度附近有**向外张开的根部树皮（板根）**，它的高度超过切口平面，一截断就会留下"从断断面往外支棱的树皮"悬在空中，而按树干横截面做的封盖盖不住更宽的板根。让整棵树从地面倒下去，根部和树桩/地面自然交叠，观感才对。若材质用的是"切口遮罩 + 抖动淡出"那套（`step(H,P.z)` 之类），**不截断只需要把遮罩高度参数压到模型最低点以下**（例如 -1000，`step` 恒为 1），淡出照旧可用——不必换材质、不必删资产；截断表现留一个 CVar 备查即可（FPSGAME：`fps.Harvest.TreeFallCutAtStump`，默认 0＝不截断）。
- **材质遮罩的必然副作用是断口空心，要单独补封盖**：树干网格是空心筒，`step(H,P.z)` 只把切口以下裁掉，断口会露出筒内（用户 2026-09-26 反馈"树倒下的阶段面是中空的"）。闭合办法不是补筒壁，而是**把重制网格里本来带的那圈真实封盖面单独提取出来贴上去**：`GeometryScript_AssetUtils.copy_mesh_from_static_mesh(静态网格, DynamicMesh(), GeometryScriptCopyMeshFromAssetOptions(), GeometryScriptMeshReadLOD(lod_type=SOURCE_MODEL))` → 用 `GeometryScript_Materials.get_triangle_material_id` 统计每个材质号的三角形数 → `delete_triangles_by_material_id(网格, 其它材质号, True)` 只留切口材质 → `remap_material_i_ds(网格, 切口号, 0)` → `GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(网格, 资产路径, GeometryScriptCreateNewStaticMeshAssetOptions(enable_collision=False))`。5.8 里 `EditorStaticMeshLibrary` 与 `StaticMeshEditorSubsystem.set_material` 都不可用，赋材质用 `UStaticMesh.set_material(槽号, 材质)`；三角形计数用 `DynamicMesh.get_triangle_count()`（`GeometryScript_MeshQueries` 没有这个函数）。提取出的封盖**顶点仍在原骨架/树本地坐标**（切口高度就是它的 Z 中心），所以挂到倒树骨骼组件下时**不要加任何偏移**；把它的材质实例并入与树干同一份 MID 列表即可一起淡出，并随骨骼组件 `SetVisibility(false, true)` 连带隐藏。
- **新增 `UPROPERTY` 后不要用 `/Zs` 之类不跑 UHT 的语法检查判成败**：UHT 输出（`*.generated.h`）还是旧的，会报 `UCLASS`/`GENERATED_BODY()` 宏未展开、"缺少类型说明符"的**假错误**（2026-09-26 实际被误导一次）。真判据是让 UBT 跑一次 UHT+编译，日志里出现 `Compile [x64] <文件>.cpp` 且无 `error C` 才算过。
- 原树材质若使用 Material Attributes，保留完整属性链；`SetMaterialAttributes` 的动态输入受 Python 访问限制，必要时用小型 Editor C++ 桥接创建输入，不用重新拼一个只剩颜色的材质替代。
- 新上段仍为骨骼网格时，断面材质需要骨骼网格 usage；**上半段还走 Nanite，断面材质必须同时带 `used_with_nanite`；树桩切面画在静态实例上，则需要 `used_with_instanced_static_meshes`**。缺哪个标志，游戏里那块就整块替换成默认材质（2026-09-25 实测：倒树断面与树桩切面都变默认灰）。核对最省事的办法是倒树那一秒的 `Saved/Logs/FPSGAME.log`，会打 `missing usage flag …! Default Material will be used in game.`。地面树桩可使用不透明材质，上半段单独支持渐隐，避免共享淡出参数使固定树桩消失。
- 不在两个 commandlet 中同时读写同一素材包；Windows 包文件句柄曾导致另一个进程保存失败。按依赖顺序完成导入和材质保存。

项目入口：`Source/FPSGAME/Production/ProductionTreeFallPlan.cpp`、`ProductionHarvestSubsystem.cpp`、`ProductionFallingTree.cpp`、`ProductionTreeHealth.{h,cpp}`，以及 `SourceAssets/HarvestTimber20260913/{export_tree_sections,cut_tree_sections,import_tree_sections,build_falling_assemblies}.py`。当前资源与恢复范围以项目 `Docs/TreeCutHingeFix-20260913.md`、生命值口径以 `Docs/ProductionTreeHealth-20260925.md` 和整理清单为准。
