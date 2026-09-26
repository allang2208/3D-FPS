# 用 Python 造材质／材质实例：实战踩坑表

> 正本／相关记录：`Docs/Building/fountain-water-20260918.md`。本文件只保留可复用技法，任务过程与数值以正本为准。

> 本文件由 `asset-model-workflow/SKILL.md` 按「复用面」拆出；入口只留触发表指针。
## 用 Python 造材质／材质实例（2026-09-18 喷泉水体，实战踩坑表）

2026-09-19 边缘溢流 V7 制作补充：
- 显式流向数据可用 `GeometryScriptSimpleMeshBuffers` 的 UV0/UV1，经 `append_buffers_to_mesh` 写入；UV1 存层号/时间时，关闭自动光照 UV 并启用全精度 UV，避免重建覆盖数据。
- 命令行制作中 `get_editor_subsystem` 可能返回 None；此时才用 `new_object` 创建所需编辑器子系统。
- Niagara HLSL 输入解析器可能将 `Particles.UniqueID%4` 当作变量名；本次改用 `fmod(float(Particles.UniqueID),4.0)` 完成资产编译。
- 资产完成标记应在整套内容写入、必要编译与保存完成后设置，避免中断后把空白副本当成成品。
- 制作计数和粒子预算不等于实机性能结果；测试与截图只按用户明确要求执行。

V8 自然随机性续篇：环状水帘用周期噪声保证环向接缝连续，以 `时间 - 飞行时间` 传播疏密变化；
慢变化管水束，快变化管碎边，各层/实例使用不同偏移。粒子随机初始条件应在出生时保存，更新时只推进轨迹。
Niagara 的发射器脚本仍走 CPU VM，即使粒子设为 GPU；本机 VM 不支持 HLSL `smoothstep`，
平滑插值改写为 `t*t*(3-2*t)`（先保证 t 在 0–1）。实例预算不因新增随机性而放宽。

项目里已经有一套成熟的"无头 Python 造材质"路线（先例 `Tools/Building/create_voxel_assets.py`、
`Tools/ZombieDog/install_random_wounds.py`、`Tools/Building/create_build_preview.py`）。喷泉那轮又补了几条：

1. **`create_asset` 要工厂实例**：`TOOLS.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())`
   —— 传**类**会报 `Cannot nativize 'MaterialFactoryNew' as 'Factory'`；材质实例用
   `unreal.MaterialInstanceConstantFactoryNew()`。顺带：本版 Python **没有** `unreal.StaticMeshFactoryNew`
   （静态网格容器要靠 `duplicate_asset` 复制一份源资产）。
2. **引脚名**：`MaterialExpressionTextureSample[Parameter2D]` 的 UV 输入叫 **`UVs`**（不是 `UV`）；
   `MaterialExpressionClamp` 的输入是**默认名**（`""`）；`Multiply/Add` 用 `A/B`，`LinearInterpolate` 用
   `A/B/Alpha`，`Power` 用 `Base/Exp`，`Fresnel` 用 `ExponentIn/BaseReflectFractionIn/Normal`，
   纹理采样节点取单通道用输出名 `"R"`。连错时 `connect_material_expressions` 返回 False **但不抛异常**——
   必须逐条检查返回值，否则会得到一个"能编译但没接对"的材质。
3. **`recompile_material` 返回的是错误列表**：`[]` ＝ 编译通过；`bool([])` 是 False，别拿它当 bool 判。
   结构自证可以用 `get_material_expressions().Num()` 加上
   `get_material_property_input_node(mat, MP_EMISSIVE_COLOR / MP_OPACITY)` 看输出挂在哪个节点上。
4. **`FCustomInput` 没有 `input_type`**（5.8 会报 `Failed to find property 'input_type'`）：
   Custom 节点的输入类型**跟着接入的表达式走**，只设 `input_name` 即可。
5. **特效网格不要依赖网格 UV**：本工程网格走 XAtlas，UV 方向不可控。水膜/泡沫/水帘这类"要按方向滚动"的材质，
   使用作者明确写入的流向 UV，或从逐像素位置自算柱面 UV。`WorldPosition − ObjectPositionWS`
   只去掉平移，不是旋转后的物体局部坐标；需要随构件旋转/缩放时用 World→Local 变换。
   **不可直接拿 ObjectPositionWS 算花纹**：它是每个物体的常量，会让所有像素采到同一点。
6. **实例参数写不进去也别慌**：`set_material_instance_scalar/vector/texture_parameter_value` 在 5.8 常返回 False
   但**实际写成功**（ZombieDog 那轮已记）；判断依据是 `scalar_parameter_values / vector_parameter_values /
   texture_parameter_values` 里出现的覆盖项名字与数量，把这份清单打进日志，用户才能知道有哪些旋钮可调。
7. **无头 commandlet 里没有关卡编辑器状态**：`LevelEditorSubsystem.is_in_play_in_editor()` 会
   `ACCESS_VIOLATION` 崩进程（喷泉那轮又踩一次）；无头脚本用环境变量护栏跳过 PIE 查询，
   加载关卡用 `LevelEditorSubsystem.load_level()` 是安全的。
8. **材质已被引用时不要重建它的表达式表**（2026-09-18 喷泉水面 v6，崩了两次）：
   `MaterialEditingLibrary.delete_all_material_expressions(mat)` 对**已被已保存的网格/材质实例引用**的材质
   会断言 `!IsRooted()`（`UObjectBaseUtility.h:209`）并直接杀掉进程。规矩：
   - 常态化做法是**只改材质实例参数**（`set_material_instance_*` + `update_material_instance`），图不动；
   - 非要改图：先删掉引用它的实例（并把网格槽指过去之前不要保存），或**换一个新的材质资产名**再建；
   - 脚本里写成"已存在且有表达式 → 跳过重建并打印提示"，就不会因为重跑而崩。
9. **别用 PowerShell 的 `Set-Content`/`Out-File` 改写源文件**：PS 5.1 会加 UTF-8 BOM、换行也可能被改，
   中文注释在 `Select-String` 默认编码下还会显示成乱码（看起来像文件坏了，其实只是读法）。只读检查用
   `-Encoding UTF8` 或 Python `open(..., encoding="utf-8")` 读；真要改文本走 `apply_patch`。
10. **XAtlas 网格上的法线扰动可能完全无效**：切线空间法线依赖网格切线基，而切线基来自 **UV 梯度**；
    本工程网格走 XAtlas（岛方向随机、局部可能退化）→ 算好的涟漪法线被乱掉的切线基转掉，
    观感就是"一块没起伏的平板"。**水平面（水面、地面贴花）改用世界空间法线**：
    `mat.set_editor_property("tangent_space_normal", False)`，材质里直接给 `(x, y, 1)` 这种向上法线。
    一个属性解决，不改图、不依赖 UV。
11. **"动感"不要只靠一张贴图**：贴图偏平时滚动几乎看不见。确定可见的做法是
    **程序化条纹（sin 波）+ 贴图**叠加，滚动方向由自算柱面 UV 的 v 决定；
    要改已投产材质的图时**新建一个资产名**（重建被网格引用的材质会断言 `!IsRooted` 崩进程）。
12. **拿现成材质当"底板／衬底"前先查 blend mode**（2026-09-18 喷泉"像固体"真凶）：
    包内 `M_Caustics` 是 **`BLEND_OPAQUE`**，拿它垫在盆底＝每个盆一块**不透明平板**，
    透过半透明水看下去就是"实心地板"——**水面波浪做得再好也改不了盆底的读感**。
    要"只加光"就自己做 **ADDITIVE + Unlit** 的材质（把花纹只接到 Emissive），
    让下面的实体表面照常可见；参数名与原实例保持一致，旧覆盖项才能继续生效。
13. **诊断顺序：先证明"运行态用的是哪套资产"，再谈调参**：
    ① 只读探针读资产属性（blend / shading / TLM / tangent_space_normal / WPO 与 Normal 接在哪个节点 / 参数默认值），
       并且**设完立刻读回**（本版枚举名写错会静默退回默认值）；
    ② 读 `Saved/Logs/*.log` 证明那次 PIE 进的是哪张图、编译了哪些系统、用的是哪次烘的资产；
    ③ 读 `Saved/SaveGames/*.sav` 证明玩家**有没有摆过**该构件（本例据此排除了"旧构件干盆"假设）；
    ④ 给构件加**运行期一次性日志**（组件 / 网格 / 槽 0 材质 / 可见性），一条日志定性"到底渲染了什么"。
    这四步比"再猜一轮参数"快得多 —— 本例连续 5 轮盲调没解决，靠 ① 立刻定位到不透明衬底。
14. **`MaterialExpressionObjectPositionWS` 是"物体原点"常量，不是逐像素位置**（2026-09-19 喷泉水体
    v5–v10 六轮"像固体"的**唯一根因**）：拿它当 Custom 节点的位置输入，波高场/法线/柱面 UV 全部在
    **常量点**求值 → 水面整体刚性升降（看不见）、法线均匀倾斜（无明暗变化）、水帘条纹与泡沫/焦散
    采样单一 texel（平板/隐形）。**`WorldPosition − ObjectPositionWS`**（Subtract 节点）是去平移的逐像素坐标，
    并未去除旋转/缩放；真正局部坐标应使用 World→Local 变换。判别法：隐藏水面网格拍一张 + 把 WaveHeight 调 3 倍拍一张，若轮廓/明暗
    都不变即命中此坑（参数读回全对也照样命中）。
15. **编辑器模式（非 PIE）关卡里没有太阳/天空**：昼夜是运行时 BP（如 `BP_FPS_DayNightManager`）在
    BeginPlay 生成的，编辑器视口/SceneCapture 拍出来是**夜景黑地**。实拍自检前先临时 spawn
    `DirectionalLight`(intensity 10–30) + `SkyAtmosphere` + `SkyLight(real_time_capture=True)`，
    拍完销毁、**不存关卡**。SceneCapture 配方（5.8 远程通道实测）：
    `RenderingLibrary.create_render_target2d(world,w,h,RTF_RGBA8_SRGB)` →
    `comp.set_editor_property("texture_target"/"capture_source"(SCS_FINAL_COLOR_LDR)/"fov_angle")` →
    每视角 `set_actor_transform(Transform(loc, look_at 四元数), False, True)` + `capture_scene()`×4 →
    `RenderingLibrary.export_render_target(world, rt, dir, name)`（**产物无扩展名**，要自己补 .png；
    Niagara 在编辑器 capture 里不 tick，水柱/粒子拍不到）。
16. **PIE 进行中远程脚本会静默早退**：脚本开头的 `is_in_play_in_editor()` 护栏 raise SystemExit(0)，
    表现为"success=True 但零输出零产物"；先等 PIE 结束（日志里出现 TRAVERSAL/输入行 = 正在 PIE）。
    另外**编辑器启动未完全就绪时**往远程通道发"重建材质"类命令会触发 MaterialEditor 的
    `!IsRooted()` 断言崩进程——等 `Engine Initialization) Total time` 日志后再发。
17. **滚动纹理的方向与"复制感"（2026-09-19 喷泉水帘）**：①柱面 UV 取 `v = −P.z/S` 时，
    `uv + (0,T)` 是**向上**流（特征点 z = S·(T−c) 递增）；要向下，所有含 T 的相位写成
    `(u·a + v·b − T·c)` 且 b,c>0。**验证法**：FlowSpeed 临时调到"3 s 位移 < 图案半周期"（如 0.05），
    同机位间隔 3 s 拍两张，离线对目标带做垂直互相关取 argmax dy（dy>0 = 下移）；正常速度下间隔太大
    会**混叠**得 dy=0 假阴性。②"几乎一模一样"的两个来源：纯 `sin(u·N)`（N 整数）绕圈精确复制、
    贴图整数平铺同理 → 用**非整数列尺度**采样噪声/贴图（唯一缝落在背面子午线）+ 逐列噪声调制
    相位/宽度/亮度。③重构材质图时**逐条核对每个算出来的场是否真接到了输出**（V4/V5 的 streak
    算了没接，画面只剩泡沫层读作平板）——`get_material_property_input_node` 只能查末级，
    中间场要顺着 Multiply/Add 链走一遍。
18. **归档前复核引用别用 `grep "名字."`**：uasset 导入表里的父级/槽引用不带尾点，会漏判
    （2026-09-19 把活跃的 `M_FountainWaterFilmV2` 当废案移进 trash 一次，靠 MIC 包字节扫描发现后恢复）。
    正确做法：扫候选资产包字节里的名字表（`re.findall(rb'M_名字[A-Za-z0-9_]*', bytes)`）或直接读
    MIC 的 `parent` 属性 / 网格的 `get_material(i)`；移完再列一遍 Materials 目录对账"应保留清单"。

## 材质函数、RT 资产与图枚举限制（2026-09-26 草交互 GPU 排障，UE 5.8 本机实测）

| 想做什么 | 坑 / 结论 |
| --- | --- |
| 在材质函数图里建节点 | `MEL.create_material_expression` 只收 `UMaterial`；函数图必须用 `create_material_expression_in_function`（Python 绑定强制声明类型，传错报 "Cannot nativize 'MaterialFunction' as 'Object'"） |
| 重编译材质函数 | `recompile_material` 只收 `UMaterial`；函数用 `MEL.update_material_function(fn, None)`——会级联重编译所有引用它的材质 |
| 读材质图节点列表（事后修接线） | **做不到**：`UMaterial.Expressions` 对 Python 是 protected（"Property 'Expressions' ... is protected and cannot be read"）。已存在的 MF 调用节点无法脚本重接线——设计时就把函数输入做成内部自供（WorldPosition/VertexNormalWS/TexCoord 节点直接建在 MF 里），调用节点只取输出、零接线 |
| FunctionInput 没接线会怎样 | 静默取 preview 默认值（通常 0），**不报任何错**——HeightMask=0 把 WPO 输出恒置零，实机表现为"完全无反应"，是最难定位的断点 |
| 建 RenderTarget 资产 | 工厂类名 `TextureRenderTargetFactoryNew`（**不带 "2D"**，`TextureRenderTarget2DFactoryNew` 不存在）；其 `Width/Height/Format` 是无 Edit 标记的 UPROPERTY，Python 视为 protected 拒设——先按工厂默认创建，再在资产上设 `size_x`/`size_y`/`render_target_format`（这些是 EditAnywhere） |
| RT 资源刷新 | `TextureRenderTarget2D` 在 5.8 Python **没有** `update_resource()`（那是 `UCanvasRenderTarget2D` 的 API）；`set_editor_property` 已触发 PostEditChangeProperty 自动重建资源。`b_auto_generate_mips` 同样不可设（RT 默认无 mip 链，实测无害） |
| TextureSample 的 UV 引脚 | 引脚名是 **`UVs`**（GetShortenPinName 规则：Coordinates→UVs），`UV`、`Coordinates` 都连不上；FunctionOutput 的输入引脚名是**空字符串**（GetInputName 返回 NAME_None） |
| Custom 节点输出类型 | Python 枚举拼写全大写带数字：`CMOT_FLOAT1`；C++ 源码拼写 `CMOT_Float1` 解析不到 |
| 材质版本标记 | `UMaterial` 没有 `description` 属性（只有 `UMaterialFunction` 有）；材质版本标签走 `EditorAssetLibrary` 的 asset metadata（如键 `GrassDeformVersion`），随资产序列化、可驱动幂等重建 |
| 给"所有实例"下发运行时纹理 | MPC 只有标量/矢量，**没有纹理参数类型**；给共享材质资产写纹理参数会污染保存内容，子系统 MID 又到不了实际渲染的 MI/foliage。可行模式：**持久 RT 资产对 + 两个 TextureSampleParameter2D 的默认值分别指向 A/B + MPC 标量（如 `ReadIsB`）uniform 分支选读侧**——默认值沿材质链继承到全部 MI，零运行时绑定 |
| 编辑器被占用时跑资产脚本 | headless runner 检测到工程被占会拒跑；对**交互式编辑器**可用桥 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript ...`（remote execution）；对 headless commandlet 持有者桥不通（无 remote execution）；编辑器重启窗口期桥的节点发现也会失败，等其 responding 后重试 |
