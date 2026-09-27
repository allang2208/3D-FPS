# FPSGAME GPU 草交互（暂停；mf-v14 候选 / pass-v7，2026-09-27）

**用户再次反馈未成功，已转待办，暂停继续调整与资产制作。** v14 原始尺寸参数未全部保存，当前本机是部分接入状态，不能写成已修复或只差用户确认。总状态见 [暂停与发布记录](../../../Docs/WorldGeneration/grass-paused-publication-20260927.md)。v13 的快速恢复未解决观感；v14 包围盒限幅发现是有源码依据的因素，但尚未证明唯一根因。只有用户重新要求开发才续接，未获测试请求不启动测试。

## 当前入口与契约

- C++：`GrassDeformSubsystem.*`；集中响应配置 `GrassDeformSettings.*`，运行时及 Python 作者共同读取 CDO，可用 `[/Script/FPSGAME.GrassDeformSettings]` 配置覆盖。默认半径 80 cm、核心 .68、强度 1、目标倾角 74°、进入 .15 s、保持 .6 s、恢复 1.8 s、低伏风 .03，行进方向权重 .97。
- 事件 API 保留 `StampTrample` / `AddImpulse`，新增 C++ `StampDirectionalTrample`，实际脚步 TravelDir 已传入形变。身体和脚步偏向行进方向；爆炸维持径向与原分来源强度／半径／波速。首版共用保持／恢复时序。
- 作者 `Tools/GrassDeform/setup_assets_m1.py`，后台入口 `run_asset_setup_m1.ps1`。必须先编译包含 GrassDeformSettings 的 DLL，再实际制作保存资产。使用 D3D12/SM6 + AllowCommandletRendering；NullRHI 不等于真实着色器编译。
- 形变 RGBA16F A/B + 接触时间 R32F A/B（四张 1024² 持久 RT、48 m 窗口）。R 是保留峰值，GB = .5 + .5 × R × 方向；A 不存时间。时间为最后接触秒数，最近点采样避免与空白时间混合。总 RT 数据约 24 MiB，不含额外开销。
- **形变／时间必须成对绘制后才切换 ReadIsB**。Stamp 与 StampTime 读取同一旧对，Recenter 与 RecenterTime 同步移动。新事件先衰减旧值再合并，不复活历史峰值；未接触像素保留原时间。Fade 为退役历史资产，r.GrassDeform.FadeHz 兼容注册但无效果。
- 材质每帧根据接触年龄执行保持＋smoothstep 恢复，没有 6 Hz 逐步减 R。读原始 RT R 只能看记录强度，不能当作当前草姿态；诊断恢复要结合时间 RT。
- 身体 MPC 每帧跟随位置／方向；历史接触 10 Hz，站立也刷新，低速不再跳过。前缘按速度 × .15 s 过渡，落地时强度也渐入。离地释放身体层；单段 >300 cm 当传送，不连线。无逐草循环、额外 trace 或运行时 GPU 回读。
- 每 stamp/recenter 两次 DrawMaterial；每帧时间标量加改变时的两个身体向量。不能沿用旧“一次 draw、一个标量”的性能承诺；v13 增加现有轴向纹理采样及旋转计算，没有性能实测。
- 参数继续放入 PN_WindParameters，不添加第三 MPC。约 4 m 平移量需量化为整数纹理像素（85 像素／398.4375 cm），不得恢复固定 400 cm 造成漂移模糊。
- 最近一次爆炸仍走 WaveOrigin / GrassWaveStartTime / GrassWaveRadius / GrassWaveStrength / WaveSpeed。旧爆炸压力记录按同一时间响应恢复，单活动波前的范围不变。
- 两个真实主材质 MA_Grass 和 M_TemperateMeadow 同步保存。原风 Add A 同时接函数 WindWPO；函数返回组合偏移减原风，避免重复叠风。
- UV1 和实例 Position and Index Texture 提供 PivotPainter 根部，INSTANCE→WORLD；所有空间场都在草根采样。v13 另以同一 UV1 读取现有 X-Vector And X-Extent Texture，复用引擎 DecodeAxisVector 得到 authored stem；从真实草轴朝统一低伏目标做最短弧旋转，整片同轴、统一角度限幅。BendAngleDegrees 现在表示目标倾角，不能再当作给原姿态追加的角度。禁止逐顶点方向采样／逐顶点位移钳制，以免重新拉宽三角。v13 偏移预算 300 cm，主材质 WPO 边界 320 cm，容纳原先逆向倾斜草片的较大旋转弧。
- 四个 RT 的 TextureObjectParameter 默认值必须指向实际持久资产；ReadIsB 分支采相应形变／时间。不能用子系统私有 MID 假装覆盖实际草地 MI。
- v14 的整片角度限幅使用材质实例 `GrassRestBoundsMin/Max`，由 `rest_bounds.py` 从原始静态网格制作并按共享材质取并集；ObjectScale 明确接 `Scale XYZ`。严禁用 `InstanceLocalBounds` 作草片长度：引擎已加入最大 WPO 余量，形成负反馈。源码作者和 `build_temperate_grass.py` 重建路径共用该边界作者，不添加运行时读取或逐草循环。
- 开关、用户开关、FoliageQuality>0 共同控制。关闭／世界退出清空四张 RT、队列、身体层、波前；仅 Game/PIE 创建子系统，防止空闲编辑器世界清草痕。离开窗口的痕迹仍不永久保存。

## 避免再走的弯路

1. **核对真实主材质。** PN 源资产和丘陵复制品不是同一个资产；只修改 MA_Grass 不覆盖 MI_Meadow_*。
2. **MPC 不能传纹理。** 草实际渲染 MI，不会使用子系统私有的 MID。使用 RT 资产作为 TextureObjectParameter 默认值。
3. **Custom 内容是函数体。** 不能在其中裸定义另一个 HLSL 函数；跨 Custom 节点也不能隐式调用局部函数。直接写表达式、语句和 return。
4. **Opaque Emissive 只写 RGB。** float4 连 Emissive 不会把第四分量存到 RT Alpha；爆炸时钟明确从 MPC 传递。
5. **UE 5.8 可后台读图。** `get_material_expressions` / `get_material_function_expressions` 可枚举；`get_material_property_input_node` 直接读取材质属性输入，不要求打开编辑器。旧“Python 无法修调用节点”的结论错误。
6. **保留输出 GUID，并处理同名重复输出。** 本次现存 MF 实际有两个 WPO，更新第一个仍让另一个执行旧代码。更新全部同名 FunctionOutput 输入，调用 `set_material_function` 刷新调用节点，并实际编译、保存依赖主材质；不要反复删整张函数图。输出身份与连接记录在 20260926-200029 制作回执中。
7. **编译结果是错误列表。** `recompile_material` 返回空列表才表示本次编译无错误；有错误应中止落盘。函数 `update_material_function` 不能替代两个实际主材质的编译。
8. **不能删启动时已 rooted 的表达式。** 以命名节点更新自有层，旧断开的历史节点不参与输出，避免 MarkAsGarbage 断言。
9. **渲染包围盒不是静态模型尺寸。** UE 5.8 InstanceDataManager 在实例边界中加入材质 WPO 膨胀量，InstanceLocalBounds 节点会读到它；用该值再次限制同一 WPO，会把 74° 目标压成小角度。保留渲染保护边界，形变约束改读作者保存的原始网格尺寸。
10. **向量参数 setter 返回值不能判成功。** 本机 UE 5.8 的 SetMaterialInstanceVectorParameterValue 已写入且更新材质，但 bResult 始终返回 false。制作脚本应读回目标参数确认后保存，不要据此误报失败，也无需再调用一次 UpdateMaterialInstance。
11. **压力记录和最终形变分开判定。** v12 的 34 项通过主要覆盖 RT、时序和捕获，不是最终顶点高度或轮廓对比。若用户要求恢复测试，应先做少量草片的固定机位启用／关闭对照，确认最终顶点转角与恢复，再看密集场和第一人称通道；不要因 RT 非零就排除材质后段或可见性问题。
12. **部分落盘必须显式标识。** MF／主材质 metadata 更新不代表所有 MI 参数同步。v14 主材质已保存而实例参数未完成时，不得继续标注全系统已更新；保留回执、失败证据和退回边界。

## 脚步反馈与操作边界

脚步尘土、贴花为独立 M3，已经另行修正。见 `Docs/WorldGeneration/footstep-black-blocks-20260926.md`；作者脚本是 `author_footstep_puff.py` / `repair_footstep_decal.py`。不能恢复 NE_Heat 的旧 Renderer 材质或 Surface 域贴花。

工程空闲才运行后台资产作者；现有编辑器占用时用 `Tools/AssetPipeline/mcp_call_codex.ps1` 批次互斥。普通 DLL 构建用 `Tools/Build/Build-Editor.ps1`，不杀其他进程、不发跨任务协调消息。Content/Plugins 不入 Git，源码落盘不等于资产落盘。

`GrassDeform.Status` / `DumpRT` / `Stamp` / `Impulse` 和 `-GrassDeformAudit` 是按用户请求使用的诊断入口，**本 SKILL 不授权主动运行它们**。交付区分源码、编译、已保存资产与用户视觉确认；没有实机测试就不要写“草已验证正常”。
