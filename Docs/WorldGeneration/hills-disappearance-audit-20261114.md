# 丘陵植被瞬间消失审计（2026-11-14）

用户报告原地、移动和转视角均会发生。此前短距离转身及 4 米相机移动测试不能排除该问题。本次把“PCG 已生成”“组件存在”“有渲染代理”“画面可见”分别记录，不互相替代。

用户进一步确认消失后 **不到 1 秒自行恢复**。这使每秒截图不足以排除问题，需要连续帧与实例状态对照，继续检查瞬时渲染 / 遮挡 / 淡出路径，不能直接认定为分区回收。

16:30 用户补充：**整个模型消失，包括树干**。优先比较实例生命周期 / 渲染代理与遮挡、GPU 绘制状态；单纯叶片 alpha / mip 问题不能解释整个模型一起消失。

**当前结论：已检查下表所列加载、场景与资源生命周期路径，找到预算设置、材质制作及远景扩大 PCG 边界的问题；尚未捕获用户报告的消失帧，不能确认瞬间消失或草层加载慢已经解决。**

## 审计路径与当前结论

| 路径 | 实际检查内容 | 结论 / 边界 |
|---|---|---|
| 地图与入口 | `TemperateHillsWorld` 构造、BeginPlay、StartWorldPipeline、客户端初始化、会话存档、EndPlay；保存地图的四层组件 | 保存地图开启半径覆盖，64/64/32/16 米图网格匹配；未发现旧地图关闭覆盖。只读地图审计初版没有读取到 policy 方法，不能拿该错误证明运行时 policy 有问题。 |
| PCG 激活与半径 | ActivateVegetationLayer、SetVegetationGenerationRadius、TickStreaming 近远分区推进；原生 RuntimeGen scheduler、change detection、player source manager | 原生 refresh 仅在每层激活调用；半径推进不调用 refresh。清理半径保持各层最大生成半径 × 1.3；方向仅影响优先级，运行时禁用视锥清理。未找到原地周期性全图清理调用。 |
| 地形异步替换 | terrain jobs、edit revision、pending collision、visible swap、view ring、backdrop coverage | 保留旧地形直到新碰撞就绪；替换对象是地形，未找到清空植物组件的调用。Backdrop 更新自己的地形覆盖纹理和组件。 |
| 植被资产分批加载 | surface handle、Solids / Understory / GroundCover / Atmosphere、依赖门槛、typed asset readiness、warmup | 林下与草层均等待三个邻域批次；初始资源句柄由 Streaming 状态持有，离场后移交 GameInstance 的 BiomeHandles。未发现定时释放植被资源句柄。 |
| 生成点与邻域 | HillsPCG、VegetationPlacement、HillsPlacement、Grass、ForestUnderstory、Microhabitats、Dressing、GroundDebris、RiverEcology、PebbleShore | 按种子、地形、水岸、资源与采集数据构造点；邻域关系按生成任务持有。生成回调只在主线程执行。候选点剔除不会删除已生成组件。 |
| 地形编辑 / 采集 | DestroyGroundCover、ClearCoverForEdit、NetEdits、CompleteProductionHarvest、FallingTreeNetwork、GrowthPresentation、HarvestSubsystem | 草清除限于编辑位置和匹配资源；树采集限于匹配实例位置；生长 / 树桩系统管理自己的组件。没有同时删除整片树与草的定时入口。 |
| 风动与天气 | ForestAtmosphere、DayNightSky、GrassDeform、DynamicWindSubsystem 的 scene recreate 回调 | 常态更新 MPC、风参数，不主动清理 PCG。DynamicWind 回调按 World 过滤；UI 预览释放自身场景不能仅凭时间相关性认定为丘陵清理。 |
| 材质与距离裁剪 | 109 个调色板网格、124 个材质及父链、四张 PCG 图的已保存属性 | 审计样本资源均可加载；树的淡出为 200–230 米，草为 35–50 米；树材质的近身淡出开关为 0。草为非 Nanite、成熟树为 Nanite，单纯修改 Nanite 参数不能解释全部症状。样本不等于所有传递依赖均已验证。 |
| 场景外部影响 | TransitLoading 的预算与资源保留、ColdSteelPreviewScene、FPSDeformationResidency、运行时画质 CVar 写入搜索 | 预览场景按自身 World 清理；驻留插件调整 GPU heap 优先级，不清空实例。未找到周期性写入 foliage density / view distance 的项目逻辑。GPU 实际绘制仍需动态证据。 |

## 确认并修正的问题

`HillsStreaming::AcquireStreamingBudget / ReleaseStreamingBudget` 使用不指定最小优先级的 `SetWithCurrentPriority`。用户实际日志在进入和离开丘陵时均产生 UE 5.8 的 constructor-priority 禁止替换警告，涉及 `pcg.FrameTime`、`pcg.RuntimeGeneration.NumGeneratingComponents` 和 `s.AsyncLoadingTimeLimit`。引擎 `ConsoleManager.cpp::ResolveContext` 明确把此情况解析为 `SETBY_ERROR`。

改用带 `FPSGAME.HillsStreaming` 标签的 `ECVF_SetByPluginLowPriority` 设置，最后一个丘陵世界退出时按相同标签 `Unset`，保留更高优先级的设备与控制台设置。仍共享原有世界计数。此修复解决预算的设置 / 恢复缺陷，**尚不能单独证明解决画面消失**。

`SETBY_ERROR` 并不等于 setter 一定没有改变数值：引擎随后仍比较优先级。此处确认的是非法优先级用法及无法恢复优先级栈的问题，不据此声称旧预算完全未生效。

另外确认两类资产缺陷，修复脚本为 `Tools/WorldGeneration/repair_hills_audit_materials.py`：

- 两种枯枝、苔藓石的 Nanite 材质使用标记未保存。六种蘑菇共用的 glTF 实例直接继承引擎插件材质，该父材质缺少实例化使用标记。已准备修复脚本，为蘑菇复制项目内父材质并补齐实例化 / Nanite 标记，保留实例参数，不改引擎资源。**这批资产尚未保存，不能称为资产修复已交付。**
- `M_FallingBeech` 在 SM6 编译时报 `Cannot cast between non-numeric types float3 to ShadingModel`。制作函数 `AddVisibilityMaskPin` 只接受丘陵目录，拒绝采集榉树目录并返回 `INDEX_NONE`；Python 使用 `[-1]` 选中了错误引脚。源码已放行精确的榉树母材质路径，制作脚本拒绝负索引；修复脚本将只重建原有裁切 / 淡出包装节点，不重新导入网格。**资产重建仍待执行。**这是倒伏树材质错误，不能冒称为站立树闪烁的根因。

## 运行证据与未完成项

- 用户原试玩 `Saved/Logs/FPSGAME.log`：14:10:52 记录 `HILLS_READY`，准备 45.355 秒；14:15:45 离开丘陵。稍后的只读观察实际采到主场景，组件数为 0，**不作为丘陵通过证据**。
- 资产 / 地图只读结果：`Saved/HillsDisappearanceAudit20261114/render-assets.json`、`map-state.json`。
- 私有编译：`Saved/HillsDisappearanceAudit20261114/Compile/`，只替换私有链接输入中的 streaming 和 diagnostic 对象，不覆盖正在由其他工作编译的对象。
- 当时生产 Editor 构建：`Saved/BuildEditor/build-20261114-151305.log`，`Result: Succeeded`。它包含流送预算修复；16:35 复核发现榉树路径放行此前加到了 `AddWindOffsetPin`，实际使用的 `AddVisibilityMaskPin` 仍未放行，因此该次构建不包含完整的榉树修正。现已修正后者，使用私有模块和隔离材质制作宿主接入，尚不能称新源码已发布到生产 DLL。
- 14:40 启动的空白档案测试在正式观察前停止。改用 `ColdSteelPlayer_PIE_0` 的 A/B 存档及校验文件副本，复制到隔离目录并记录 SHA-256；原玩家存档不写入。
- 14:42 隔离运行：`Saved/VegetationStreamingCheck/20261114-144246/`。原地 90 秒、其中第 45 秒 GC、相机跨分区 150 米往返、360 度转向、最后停留。每 0.1 秒核对附近组件数量 / 注册 / ShouldRender / SceneProxy，截图约每秒一张。相机路线测试 PCG 视点流送，不冒称真实步行 / 碰撞验收。
- 独立运行已完成 210 秒观察：1,250 次状态采样、185 张图，25 米范围内的既有组件未出现数量下降、注销、ShouldRender 关闭或 SceneProxy 丢失。初始近处 298 个组件；全场统计约 126,286 个静态实例和 3,825 个蒙皮实例。此断言只覆盖组件状态及 25 米范围，不覆盖远处所有可见树木。
- 原地画面与路线抽帧分别见 `stationary-sheet.jpg`、`route-sheet.jpg`；静止段的草地区域绿色像素占比约 0.913–0.919，未见整片消失。截图约 1 Hz，不能排除亚秒级闪烁；像素占比不是 GPU 正确性的证明。
- 此轮 `HILLS_READY` 为 133.893 秒，输入放行约 155.738 秒，随后 80 米草层扩展 26.192 秒；雨林转移后 32 米草层就绪 23.385 秒。冷资源编译、其他构建及本次读取造成的额外 I/O 均干扰性能，**不能据此给出加载速度已达标结论**。
- 原生诊断输出 `pass=1` 后，在引擎退出阶段出现 Renderer 空地址访问异常。因此该轮不是正常退出的完整通过；退出异常尚未定位，也不能当作游戏中闪烁的证据。
- PIE 尝试 `20261114-145835` 因 Python 不暴露 EditorLoadingSavingSettings 而未开始，已修正为配置覆盖；`20261114-150341` 已请求 PIE，但进程在资产注册表等待期间结束，没有 HILLS_READY 或诊断结果。终止来源未确认，不计为 PIE 测试通过。用户原始问题仍未成功复现。
- 15:43 读到用户实际 `UEDPIE_0_L_TemperateHills_Initial`，同一世界种子；该次准备约 40.008 秒。随后在连续帧挂接前收到 CloseEditor 退出，录制没有启动，不能用作观察通过。已准备独立的逐帧诊断模块，扩大组件观测范围到配置淡出终点内 10 米，并在发现状态丢失后继续记录恢复过程。
- 用户 GameUserSettings 保存 2560×1440 / Epic 画质；首轮隔离测试强制 1280×720。逐帧启动器现复制画质配置并读取同一分辨率，避免将低负载结果直接外推到用户环境。
- 仍需区分：生产 DLL 构建发布与私有诊断 DLL；独立运行与 PIE；单机与多人。未测试的项目不能写成通过。

## 当前执行边界

- UE 批次锁 `Local\CodexUeMcp-Port-8000` 两轮各 15 分钟等待超时，另一次接入前检测到仍在退出的编辑器而停止。本次没有启动资产写入：`MaterialRepair/saved.json` 和 `material-repair.log` 尚未生成。
- `FrameCompile/UnrealEditor-FPSGAME.dll` 已私有编译 / 链接成功，使用 1,043 个固定的当前工程链接输入；90 秒逐帧复验尚未运行，`frame-run.json` 未生成。
- 16:04 再次提交生产 Editor 构建，停留在 `Build.bat` 全局构建锁等待；当时另一个完整 Game 构建正在运行。16:11 已撤销本次等待，没有中断原有构建。该次没有进入 UBT，也没有生成新的生产构建日志；最新逐帧诊断目前只完成私有模块编译，不能称为已发布到生产 DLL。
- `capture_hills_live_frames.py` 准备了不移动玩家的实际 PIE 连续帧记录，但挂接时编辑器已退出、远程节点不可用，没有录制结果。
- 后续具体批次已准备为 `Saved/HillsDisappearanceAudit20261114/Run-RemainingAudit.ps1`：先备份并保存 8 个材质资产，再运行隔离 PIE 逐帧观察。该脚本持有同一 UE 批次锁，并检查现有编辑器 / 渲染器和丘陵资产写入冲突，不会自动关闭它们。
- 草叶 / 树叶的透明贴图流送、alpha mip coverage 和虚拟纹理属性已加入只读审计脚本；扩展读回尚未执行。不能把这些候选路径认定为根因，也没有盲目更改全局遮挡、Nanite、毛发或纹理池设置。
- 续查将逐帧模式改为保留玩家的视角目标与第一人称身体 / 毛发可见性，只调整控制器朝向以取到附近树木；旧观察相机会改变这些条件。16:25 私有诊断模块重新编译 / 链接成功，日志为 `FrameCompile/first-person-compile.log` 和 `first-person-link.log`；尚未开始本轮运行。请求的分辨率来自玩家设置，实际 PIE 渲染尺寸仍需从输出帧核对。
- 只读材质审计扩展到 `GetMaterialUsedTextures` 和递归材质函数表达式，覆盖藏在函数内部的透明贴图与裁剪节点。此扩展尚未执行，不增加已审计资产数量。
- 16:44 私有模块又加入 `MarkRenderStateDirtyEvent`、渲染代理地址变化与 PSO 等待状态的诊断日志，编译 / 链接成功（`proxy-compile.log`、`proxy-link.log`）。这覆盖“实例数量不变但绘制状态重建”的情况；不保留组件强引用，不改变正常草木剔除。逐帧启动器另外启用原生 PCG 生成 / 清理 / 刷新日志，仅对隔离诊断生效。
- 续查 16:36–16:51 的 15 分钟接入等待再次超时（`UE batch wait expired; nothing started.`）。修复和录制进程均未启动，三个输出 `MaterialRepair/saved.json`、`material-repair.log`、`frame-run.json` 仍不存在。现有资产制作进程保持运行，没有中断它。此前两次为上一轮等待，本次单独记录。
- 16:56 最终私有模块构建完成，退出清理会注销渲染事件订阅，提前退出也不会留下悬空回调；`proxy-cleanup-compile.log`、`proxy-cleanup-link.log` 对应成功的编译 / 链接。4 份本轮 Python 脚本及批次 PowerShell 通过语法解析。没有本轮运行通过证据，没有后台排队遗留。

## 继续从代码侧排查

本轮只读取工程与本机 UE 5.8 引擎源码、修改源码和进行私有编译 / 链接，没有启动 UE、写入资产或运行游戏。

### 已确认并修正：远景扩大植被生成边界

- `PCGHelpers.cpp::GetGridBounds` 对普通 Actor 调用 `GetActorBounds`，后者遍历 Actor 的所有 PrimitiveComponent；并非只采用名为 `WorldBounds` 的盒体。未注册组件也参与合并，只有带 PCG 生成标记的组件被排除。
- `TemperateHillsBackdrop.cpp::TickBackdrop` 原来把三个远景地形组件创建在 `ATemperateHillsWorld` 上。外圈的 `OuterHalf` 为 **512000 厘米 / 5.12 公里**，远大于最大地图的 512 米半边长；远景树也属于同一 Actor。因此远景加入后 PCG 的原始生成边界会扩大，地图边缘附近还会调度可玩区以外的网格。项目自己的 `CountVegetationCells` 只统计可玩边界，二者口径不同。
- 修正为同一 Level 内的临时表现 Actor，远景地形和 HISM 树冠组件都归它所有，根组件仍附着原丘陵根组件，保留相对位置。`EndBackdrop` 按新组件 Owner 释放组件并销毁该 Actor。它通过普通组件附着，不使用 `UChildActorComponent`；引擎 `ForEachComponent(true)` 不会把普通附着 Actor 的组件并入丘陵边界。
- 没有给远景伪造 `PCG Generated Component` 标签来规避边界：引擎的孤立资源清理会删除带此标记但不受 PCG ManagedResource 管理的组件。
- **影响边界：**修正远景造成的生成范围扩张和边缘额外调度，不保证具体加载提速。原生 change detector 并不因为边界扩大而直接刷新整层；尚未建立这项问题与原地亚秒级闪烁之间的因果关系。预热组件和其他丘陵自有组件仍按引擎规则参与边界计算，不能称所有源边界已经改为固定盒体。

### 进一步核对的路径

- **生成源 GC：**`UTemperateHillsGuestSource` 在项目表内是弱引用，但原生 `FPCGGenSourceManager` 以 `TScriptInterface` 保存已注册源，`AddReferencedObjects` 显式收集引用，scheduler 继续转发收集。不存在仅凭项目弱引用就能认定的随机 GC 清理缺陷。
- **生成 / 清理距离：**原生生成和项目就绪计数均使用格子盒体到源的距离，包含等于半径的情况。当前半径推进只写 radii 和 hash，不调用 refresh；清理按最大生成半径的 1.3 倍保留。朝向影响优先级，项目激活时禁用视锥清理；未发现原地定时清空整个图的项目调用。
- **地形 / 缓存更新：**新地形碰撞就绪后才替换旧地形；RVT 绑定只对地形调用 `MarkRenderStateDirty`。覆盖纹理更新针对远景材质，未发现该路径注销树草组件。
- **组件类型：**此前保存的四张图使用 ISM / InstancedSkinnedMeshComponent，远景树则明确使用 HISM。不能把近景图的组件类型结论扩展成“丘陵没有 HISM”。远景 HISM 只在创建时加入实例，本路径没有周期性重建树冠。
- **草层 CPU 工作：**`TemperateHillsPCG.cpp` 对草条带做了时间片，但 `PrepareVegetationCell` 的完整邻域准备及最后的点元数据构造仍在主线程单次执行。它们是仍需耗时证据的加载瓶颈候选，当前没有测量可证明其占比；未据此修改生成算法、密度或随意扩大预算。
- **风参数：**森林风代码更新世界所属子系统和 MPC；风速频率固定，幅度 / 方向平滑。所查路径没有组件清理或可见性翻转，不能把风参数更新直接认定为整体模型消失原因。

### 本轮落盘与构建

- 仅修改 `Source/FPSGAME/WorldGeneration/TemperateHillsBackdrop.cpp` 的远景组件所有权与清理，保留该文件已有改动。修改前副本为 `Saved/HillsDisappearanceAudit20261114/CodeBounds/TemperateHillsBackdrop.before.cpp`。
- 使用工程 Shared rsp / PCH 编译该翻译单元，并替换私有链接清单中的原 backdrop 对象；`CodeBounds/backdrop-compile.log` 和 `backdrop-link.log` 均成功，生成 `CodeBounds/UnrealEditor-FPSGAME.dll`。最初从错误工作目录调用编译器导致找不到 CoreMinimal.h；改为 Engine/Source 后编译成功，未修改包含目录来绕过错误。
- 当前另一个正式 Game 构建仍占用共享 UBT，未排队或中断它。本轮 **没有更新生产 Editor DLL**，也没有把私有旧对象快照冒充完整生产构建；此次源码修正需后续正式构建后才能进入正常启动版本。
- 闪烁根因仍未确认；既有逐帧诊断尚未运行，本轮不能新增画面或加载时间通过结论。

## 持续原地闪灭：绘制链路续查

用户本轮确认：**进入丘陵等待 3–5 分钟后仍一直发生**。这与一次性入场预热不符；仍需区分组件重新生成、渲染代理重建、GPU 剔除 / 深度输出三个阶段。没有新的运行抓帧，根因尚未确认。

### 新核对的源码证据

1. **不能用材质 usage 警告推导全场重编译。**本机 `Material.cpp::SetMaterialUsage` 明确检查 `FApp::IsGame()` 和 `GEditor->IsPlayingSessionInEditor()`。PIE / 游戏路径缺标记时使用默认材质；仅非游戏编辑器路径自动补标记和编译，而且其 UpdateContext 仅使用 `SyncWithRenderingThread`。原日志缺标记警告仍是待修资产问题，不证明播放中全场重编译。
2. **PSO 只在代理重建链路上才能解释短暂不绘制。**`UInstancedStaticMeshComponent::CreateStaticMeshSceneProxy` 和 `UInstancedSkinnedMeshComponent::CreateSceneProxy` 在 PSO pending 且策略为 `DelayUntilPSOPrecached` 时返回 nullptr；完成回调经 `UWorld::AddPrimitiveComponentPSOPrecacheCompleted` 再标记重建。项目默认 ProxyCreationStrategy=1。尚无实际闪灭帧的调用证据，未把该设置直接改掉。
3. **此前 render-dirty 监听不完备。**`FComponentRecreateRenderStateContext` 直接调用 Destroy/Create，`UActorComponent::RecreateRenderState_Concurrent` 也可直接重建，不必先调用 `MarkRenderStateDirty`。所以没有收到该事件不能排除重建；代理地址相同也不能单独证明未重建。
4. **持续风动调用并不注销草木。**DynamicWind 的 `UpdateParameters` 只赋值风参数，注册表按 FScene 分开。继续核对了骨架删除 / 数据上传索引：任务把默认分配器的 TMap 复制为 `SceneRenderingSetAllocator`，跨分配器 TSet 构造走 Append，生成紧凑索引；不能把原表可能有的稀疏空洞直接当作本项目 GPU 数组越界证据。静态草也不使用这一骨架风动通道。
5. **玩家外观定时维护有变化判断。**`FPSPlayerBodyComponent` 每 0.2 秒更新 owner visibility，但 `FPSBodyEquipment::ApplyOwnerVisibilityFlags / ApplyShadowFlags` 比较旧值后才调用 setter。未发现仅因周期到达就不断重建所有草木的调用。第一人称 Groom 保留 OwnerNoSee / 隐藏投影语义，未以关闭头发代替修复。
6. **额外的剔除路径不能假定已开启。**本机引擎 `r.InstanceCulling.OcclusionQueries` 默认 0，`r.StencilForLODDither` 默认 0；已查看的项目 DefaultEngine 没有覆写二者，实际进程仍可能受用户设置 / 控制台影响。新增诊断读取运行值，不把默认值冒充现场值。
7. **Groom / NVIDIA 深度异常仍是候选。**本轮重新查看 Epic UE-360482：记录的是 ISM 在 prepass 后的深度写入异常，状态 Cannot Reproduce，Target Fix 5.8；不是本项目已确认缺陷。论坛的 5.8.2 报告特指部分非 Nanite 树段，且报告草保持稳定；当前项目成熟树使用蒙皮 Nanite、用户还报告草闪灭，不能直接等同。
8. **实际日志有光追几何驻留异常，但发生在传送后。**现有 `Saved/Logs/FPSGAME.log` 最后写于 15:45；15:42:15 的 `fps.Hills.VisitVillage` / `HILLS_VILLAGE_LANDED` 后一帧出现 `!Geometry->IsEvicted()` ensure，提示跳过动态光追实例。核对 `RayTracing.cpp:1031`，该分支跳过的是光追实例收集，不调用草木组件隐藏 / 清理，也不能证明主视图光栅模型消失。几何名为 None，日志不能归因到具体树、草、角色或地形；此异常单独保留，不把传送事件冒充静止闪灭的根因。

### 为找到首个异常补齐的诊断代码

新增 `TemperateVegetationRenderAudit.h`，仅在已有 `-HillsVegetationFrameAudit` 模式启用：

- 主线程传稳定 PrimitiveComponentId 和期望实例数，不传组件或代理指针到渲染线程，不持有植物 UObject 强引用。
- 对目标世界的主视图，在 `PostRenderViewFamily_RenderThread` 记录代理是否进入场景、实例数据头数量、IsShown、包围盒有效性、视锥交集、实际 Nanite 代理类型及 camera cut。过滤 SceneCapture，避免把天空 / 瞄镜等视图当作主视图。
- 对变化及恢复留记录，平稳阶段仅输出汇总；不等待实例更新任务，不读回 GPU，不改变风、LOD、剔除或材质设置。**这是渲染线程输入观察，仍不等于 GPU 像素确实画出。**
- render-dirty 同时捕获调用栈原始地址；按栈哈希去重，入场记录模块 ASLR 基址与文件时间戳，供离线找调用者。另读取 PSO、实例遮挡、HZB、Stencil、Hair、Nanite 的实际 CVar。
- 修正原诊断在遇到第一个 loss 后立即返回的逻辑，继续核对其余组件并更新快照；恢复日志不再把仍无代理的组件误记为恢复。

本轮修改的是诊断代码，没有新增闪灭修复结论。独立编译和私有链接产物位于 `Saved/HillsDisappearanceAudit20261114/RenderCode/`；链接继续保留上一轮远景所有权修正。未启动 UE / 游戏，未写入材质资产，未发布生产 DLL。真正缺少的证据仍是**用户实际闪灭帧与上述状态在同一时段的对应关系**：若代理 / 实例数据同时缺失，追其调用者；若它们和视图条件稳定，才继续定位 GPU 剔除 / 深度 pass。

## 21:24 入场超过一分钟的追加处理

保存现场日志到 `Saved/HillsEntryLoading20261114/FPSGAME-before.log`：21:24:27 开始丘陵生成，21:24:49（21.86 秒）才请求三个植被批次，21:24:50 地表出生碰撞就绪（22.89 秒）；21:25:29 取消时仍无植被批次 ready / HILLS_READY。日志是 Quick 档，不能解释为用户选择完整预加载。期间有 `FlushAsyncLoading`、狐狸 / 母鹿蒙皮等待，以及多次资源编译内存预算仅约 415–700 MiB 的提示；没有 trace，不能把全部等待秒数归到单个资产。

确认并修改两个加载路径：

- `TemperateHillsStreaming.cpp` 原本从进入至游玩一直使用 2 ms 的异步加载 / PCG 预算。现在入场阶段分别为异步加载 8 ms、PCG 6 ms、关卡 Actor 注册 4 ms；解除入场输入锁后恢复原来的 2 ms。并发 PCG 仍为 8，不增加资源并发数。采用现有带标签的 CVar 覆盖，退出恢复；多个丘陵世界共存时只在全部仍处于入场阶段才加预算，避免新玩家入场扩大已游玩世界的预算。
- `WildlifeSubsystem.cpp` 原本只等 `bSurfaceReady` 就自然刷动物，`SpawnOne` 同步 `LoadObject<UClass>` 会把动物蓝图的网格 / 动作依赖插入正在加载植被的队列。改为 `bReady` 且加载界面不再持有输入后，才开始自然生成。动物种类、掉落、群体规则、90 m 暂停与 140 m 回收不变；尚未将入场后的动物加载改成异步。

保留出生点四层植被、碰撞与地面材质 / mip 就绪条件。增加每批 packages / compilation 等待日志（每 5 秒）、待编译资产名、资源读取完成时间以及实际生效的预算；加载界面显示当前类别和资源准备进度。没有同步 flush、全局关闭剔除或降低草地密度。

后台构建记录位于 `Saved/HillsEntryLoading20261114/Editor-build.log`。本次不启动编辑器 / PIE、不做进场计时；构建结果与产物状态以同目录回执为准。上述修改针对入场等待，不构成原地持续闪灭的根因确认或修复验收。

## 2026-11-15：代码续查与正常游戏中的被动记录

本轮仍未找到能够证明“原地持续、整模型消失后不到一秒恢复”的实际调用链。没有把下列排查结果当作闪灭修复，也没有修改全局遮挡、Nanite、Groom 或植被密度。

- `FPSNiagaraSceneLifecycle::OnSceneRecreated` 明确只处理 `EWorldType::Editor`，且要求编辑器场景已被释放；不是正常游戏世界的周期性注销入口。
- 再次沿原生 PCG change detector 跟到 scheduler：半径 hash 改变触发重新扫描，清理仍计算各生成源到格子盒体的距离和 cleanup radius；并不因为半径 hash 改变就无条件重建全部格子。`TickCVars` 在池开关 / 池大小改变时会全清理，但未发现项目在原地周期性修改这些值。图中 `ConsoleVariablesTriggeringRefresh` 也能触发 refresh；制作代码没有设置它，当前资产快照没有读出该字段，不能称此入口已被完全排除。
- 森林风的原生 provider 更新只写骨骼变换；草层为静态实例，不能仅靠树的骨骼风路径解释两类模型共同闪灭。没有确认相关骨骼输入异常。
- `BuildValleyFog` 更新自己池中的雾模型和材质参数，不修改 PCG 草木；预览场景的清理仍限定自身 World。

### 修正诊断覆盖缺口

旧 `HillsVegetationCheck` 需要专用启动参数，且会转向、传送、强制 GC、截图并退出进程；其旧采样间隔也不足以排除亚秒问题。旧观测器只匹配 `/Game/WorldGeneration/TemperateHills/` 路径，导入包原目录的实例不会被纳入。这些都是诊断覆盖问题，**不是已确认的游戏闪灭原因**。

新增 `Source/FPSGAME/WorldGeneration/TemperateVegetationLiveTrace.cpp`：

- 正常游戏内执行 `fps.Hills.TraceFlicker 90`，默认关闭，最多记录 300 秒；`fps.Hills.TraceFlicker 0` 停止；`fps.Hills.TraceFlicker mark` 给刚看到的闪灭打时间标记。
- 每帧末检查已跟踪的弱引用实例组件，记录实例数、注册状态、渲染状态、代理、dirty / PSO 等待变化；每秒发现新组件，覆盖 250 米范围的静态 / 蒙皮实例，不以素材文件夹筛选。离开 300 米或对象销毁 5 秒后解除跟踪，保留短暂缺失与恢复信息。
- 监听已发现的丘陵 PCG 组件开始 / 完成 / 取消 / 清理事件和 render-dirty 调用栈。渲染线程复用 `VEGETATION_RENDER` 记录代理与实例数据输入；原始栈地址配套模块基址，供事后解析。
- 不持有组件强引用，不改摄像机、生成规则或渲染配置，不强制 GC、截图、GPU 同步读回或退出游戏。到时 / 离场注销全部监听。输出到正常 `Saved/Logs/FPSGAME.log`。
- **证据边界：**这仍不读取 GPU 最终像素 / 深度结果；直接 Destroy/Create 且在同一帧复用代理地址等情况也未必被状态采样捕获。正常状态日志不能替代实际闪灭帧或证明渲染正常，结束日志明确标记 `gpu_draw_result=unobserved`，不输出 pass。

后台 `FPSGAMEEditor Win64 Development` 构建成功，正式 `UnrealEditor-FPSGAME.dll` 已更新；最终日志为 `Saved/HillsLiveTrace20261115/Editor-build-final.log`（52.65 秒）。首轮仅因本次新增代码两处局部变量遮蔽被编译器拒绝，改名后完成构建。没有启动编辑器或游戏、没有运行记录命令。目前没有新增闪灭复现证据，真正根因与最终修复仍未完成。

## 2026-11-15：用户 F6 导出包分析与修正

读取的实际包为 `Saved/PerformanceReports/gpu-F3A748134AA6280234A74C8DDA8AE076/`，含三次性能 JSON、`engine.utrace`、`buffers.jsonl` 和 `manifest.json`。同次日志冻结为 `Saved/HillsF6Audit20261115/FPSGAME-captured.log`。通过 `UnrealInsights -NoUI -AutoQuit` 离线解析已有 trace，导出 1,000,325 条 timing events 到同目录；未启动编辑器或游戏、未重新采样。

### 记录覆盖与实际发现

- 时间均按北京时间：GPU 记录开始 **01:05:51.011**，结束 **01:05:53.772**，约 **2.76 秒**，结束原因 `F6_export`。后两份 JSON 为 01:06:38 和 01:06:54，其帧窗口与这段 trace 的重叠均为 0；不能把后两次导出当成新 GPU 录制。
- `StartTraceW` 返回 Windows 错误 **5**，`capture_mode=ue_trace_only`，`files_finalized=false`；没有 `wddm.etl`。UE trace 与缓冲身份文件已收尾，但不构成完整显卡驻留证据。Insights 尾部另提示剩余 287 字节 transport buffer，分析不使用不完整的尾部 scope。
- 三份窗口平均帧率约 29.0、28.4、38.9。GPU 时间是异步观察值，不能逐行和 GT 配对。343 个资源样本的 local memory 使用量约 6,987–9,324 MiB，记录到的 over-budget 均为 0；这不排除独立的光追几何预算逐出。
- **定位到周期性主线程停顿：**GameThread 的 `TemperateHillsWorld` 在 trace time 434.360828、435.3615、436.3636 附近分别耗时约 **360.7、358.9、373.4 ms**，间隔约 1 秒。每个长 tick 内有 6 次 `ForEachObjectOfClass`，约每 60 ms 一次；日志显示本场景恢复了 6 个 terrain edits。项目一秒一次的地形编辑清草循环对每处编辑调用 `DestroyGroundCover`，其旧顺序先对全世界每个 ISM 遍历软引用草资产目录，再判定是否靠近编辑点；即便没有草需要删除，也重复这项工作。
- **树木统计缺口：**F6 的 `ReadGeometry` 只有 StaticMesh、SkeletalMeshComponent、DynamicMesh 分支，漏掉 `UInstancedSkinnedMeshComponent`。所以该包的 `Instances` / `all_mesh_asset_summary` 不涵盖丘陵成熟树；雨林低草快照从 24,449 增至 35,105，也不能证明两次快照之间没有瞬时消失。
- **01:06:10.957 的 ensure：**`RayTracing.cpp:1031` 的 `Dynamic ray tracing instance skipped because geometry 'None' is evicted` 发生在 GPU trace 已停止约 17 秒后。核对本机引擎源码，该 continue 跳过动态光追实例提交，不直接删除主画面的 raster / Nanite 代理。`None` 也不能识别具体对象。因此确认存在光追提交异常，但未将它认定为树草整模型闪灭根因。
- 01:04:51–54 与 01:05:24–27 的两次长帧同时有 PIE 内 Niagara 素材编译 / Python 操作，后一次长帧约 3.02 秒；01:06:10 的 ensure 报告处理约 2.26 秒。这些能解释部分卡顿，不能替代闪灭帧证据。没有发送跨对话消息或操作这些制作任务。
- 此次整个日志没有 `HILLS_FLICKER_START`、`HILLS_FLICKER_STATE` 或 `VEGETATION_RENDER`，上一轮独立的草木记录命令没有产出数据；不能据此声称组件 / 代理稳定。

### 本轮落盘的改动

1. `TemperateHillsWorld.cpp::DestroyGroundCover` 将 bounds 相交判断放到软引用草资产匹配之前，先排除远处组件。保留相同类型、半径、高度和实例删除条件，不改变清草范围、密度或树木规则。增加 `HillsGroundCoverEditSweep` trace scope，以便下一次直接读到该函数耗时。本次修正针对已定位的每秒重复扫描；没有运行后的耗时收益数值。
2. `FPSPerformanceMetricsScene.cpp` 增加蒙皮实例组件分支，记录树木资源、实例数、源 LOD 几何及 Nanite 数据标记；采样遇到编译中的蒙皮资产跳过资源读取，不强制完成编译。仍然是源几何统计，不是 GPU 实际可见性。
3. 在丘陵内明确点击 F6 的“GPU 驻留/调度：开始”时，同步启动既有被动草木记录；由该次 GPU capture 的弱引用控制结束，离场和最长 180 秒也会停止。手动启动的记录保留自己的时限，其他 PIE 世界的记录不被覆盖。没有启用 F6 GPU 采集时不会自动记录；不改相机、剔除、风动、GC 或游戏规则。输出仍在 `FPSGAME.log`，同时记录对应 `gpu-...` 目录。

后台 `FPSGAMEEditor Win64 Development` 构建成功，正式 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已更新。构建日志：`Saved/HillsF6Audit20261115/Editor-build.log`（32.11 秒）与 `Editor-build-final.log`（21.30 秒）。未启动编辑器或游戏、未进行运行验收；**本批资料尚不能确认整模型闪灭的真正原因，未宣称已彻底修复。**

后续有效证据需从项目现有 `Launch-F6-WddmCapture.cmd` 入口启动具备 ETW 权限的进程，在丘陵内开始 F6 GPU 采集，关闭面板并经历实际闪灭后再导出；新的草木记录随同启动，无需另输命令。第一次导出会结束 GPU 记录，继续观察后若要再捕获，需要再次开始。保留完整目录与同次 `FPSGAME.log`，仍不以总实例数或无错误日志证明画面正确。

## 2026-11-15 11:11 新采集：确认地形提交触发 PCG 全层刷新

新包为 `Saved/PerformanceReports/gpu-BACED94D43A8A8B8E5DA3C9D23F76889/`，日志冻结到 `Saved/HillsF6Audit20261115B/FPSGAME-captured.log`。本轮只离线分析用户已采集的数据，没有启动编辑器、游戏或新录制。

### 同一时段的直接证据

- 北京时间 11:11:12.652–11:11:24.927，12.275 秒；WDDM / D3D12 provider 启动成功，`files_finalized=true`，各 lost 计数为 0。ETL 为 431,226,880 字节，因 `etw_file_size_limit` 提前停止。11:11:45 的 JSON 仍引用这段已停止的采集，不能当成持续到导出时刻的 GPU 时间线。
- 用本机 xperf 解码 ETL，保留 1,457,651 条事件，未发现解码字段数不匹配。系统级逐出 / 换入事件不能按回调线程 PID 当作本进程树草的驻留结论；本轮没有建立植被资源到物理段的映射。JSON 中实际落在这段采集内的 23 次显存预算样本使用量为 8,725–8,957 MiB，over-budget 为 0；`buffers.jsonl` 有 2 个时钟锚点及 2,853 条角色 Morph 缓冲观察，也不能替代植被 GPU 可见性。本轮修复依据是同窗主线程刷新与组件 / 代理销毁链。
- 被动记录跟踪 1,285 个实例组件，记录 176 次 PCG 开始、75 次取消、118 次完成；220 个已跟踪组件随后 `alive=0`。涉及低草、花、蕨类、灌木、成熟山毛榉和黑杨，也包括岩石。
- 例如 `PCGPartitionActor_87.ISM_SM_SoftWildGrassLow_0`（id 2768，109 个实例，距离 1.4 米）在 11:11:22.047 销毁；11:11:22.062 渲染线程记录其 proxy 归零。`PCGPartitionActor_76` 的同类低草（id 3108，134 个实例，距离 1.3 米）同帧消失。不是只有材质或叶片变化。诊断按一秒发现新对象，旧对象路径也可能被 PCG 重命名，不能由这组记录精确推算全部对象的画面恢复时长。
- `engine.utrace` 的 GameThread 有 12 次真正进入 `FPCGTrackingManager::OnObjectChanged::AlwaysTrackedUpdate` 的通知，父调用全部为 `TemperateHillsWorld` tick → `OnObjectPropertyChanged` → `FPCGActorTracker::OnObjectPropertyChanged` → `OnSelectionKeyChanged`。这比单独统计 `OnObjectModified` 次数更能说明发生了刷新。
- 上轮新增 `HillsGroundCoverEditSweep` 的 72 次调用总计 13.987 ms，平均 0.194 ms，最大 0.278 ms；确认清草扫描的周期性长停顿已明显收敛，不将它冒充本次 PCG 重建的原因。

### 代码因果链与修复

本机 UE5.8 的 `UDynamicMeshComponent::SetMesh` 经 `OnMeshObjectChanged` 调用 `BroadcastMeshPropertyChangeEvent`。该函数只检查 `WITH_EDITOR`，因此 **PIE 的运行时网格提交也会广播 `OnObjectPropertyChanged`**。丘陵地面、水塘、河面的组件都由 `ATemperateHillsWorld` 持有；PCG actor tracker 将组件变化转换成其 owner 变化，component change handler 的 `bOwnerChanged` 会 dirty 所有相关分区，再通过 `Refresh` 进入 runtime scheduler，取消任务并清理 / 重建已有生成结果。

这三个 `SetMesh` 发生在后台地形结果提交时，即使玩家没有移动，也可以继续触发；它们提交的是 `Height()` / 地形编辑数据的显示与碰撞网格，植被候选本身直接读取确定性的高度场与编辑数据，不需要因网格对象提交而重新生成所有分区。

`TemperateHillsStreaming.cpp` 新增局部 `HillsStreaming::SetCellMesh`，覆盖地面、水塘、河面三个提交点：在同步 `SetMesh` 期间，使用 PCG 原生 `StartIgnoringChangeOriginDuringGeneration` / `StopIgnoringChangeOriginDuringGeneration`，让四个丘陵原始 PCG 层仅忽略当前网格组件的属性通知；由作用域退出恢复。没有关闭全局 PCG tracking、距离生成 / 回收、材质通知或碰撞更新。既有地形编辑失效、清草及采集资源删除入口照常保留。非 Editor 构建没有这条广播，直接提交网格。

源文件修改前副本、当次 DLL/PDB、解析后的状态、调用栈、GameThread 时间线及 ETL 解码结果保存在 `Saved/HillsF6Audit20261115B/`。**本次已定位并完成采集中证实的地形提交误触发植被重建路径的源码修复；修复后的实机表现尚未验收，不据此排除其他未捕获的 GPU 闪灭。**

2026-11-15 构建接入已完成：原 Game 构建及后台地图保存进程退出后，正式工程已有一轮 `FPSGAMEEditor Win64 Development` 构建接续执行，包含 `[5/8] Compile [x64] TemperateHillsStreaming.cpp` 及正式 DLL 链接，12:03:48 返回 `Result: Succeeded`，总耗时 632.85 秒。完整日志已保存为 `Saved/HillsF6Audit20261115B/Editor-shared-build.log`。确认该构建已纳入本次修复后，仅停止本轮自身的等待脚本，避免重复提交；没有终止其他编译或 UE 进程，也没有发送跨任务协调消息。

正式 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已于北京时间 12:03:17 更新，大小为 46,775,296 字节，二进制中包含新增的 `HillsSubmitTerrainMesh` 标记。源码 SHA-256 与等待编译前一致，确认落盘的是本轮修改版本。构建回执、DLL SHA-256 与源码 SHA-256 保存在 `Saved/HillsF6Audit20261115B/editor-build-receipt.json`，状态摘要为同目录 `capture-findings.json`。本轮没有打开编辑器、启动游戏或运行测试；实机闪灭表现仍由用户测试，不将构建成功等同于运行验收。

## 外部资料与采用边界（引用）

- Epic [Runtime Generation 文档](https://dev.epicgames.com/documentation/unreal-engine/using-pcg-generation-modes-in-unreal-engine?lang=en-US)：按生成源距离生成 / 清理，支持独立清理乘数。本项目已采用这一原生机制，无需先更换调度框架。
- Epic [UE-360482](https://issues.unrealengine.com/issue/UE-360482)：NVIDIA 上 Groom 可见时 ISM 深度异常；公开状态为 Cannot Reproduce，不能称为已经确认本项目根因。
- [原始 5.8.2 闪烁报告](https://forums.unrealengine.com/t/ue-5-8-2-nvidia-dx12-foliage-sections-flicker-disappear-while-groom-rbf-is-enabled/2835024)：作者报告静止闪烁、关闭 Groom/RBF 可改变表现，但未证实同一 GPU 机制。仅作复现线索，不在生产配置关闭毛发。
- GitHub [PCGEx](https://github.com/PCGEx/PCGExtendedToolkit) 提供空间操作和 PCG 节点；[Procedural Surface Terrain Generation](https://github.com/ShotaKhakhishvili/Procedural-Surface-Terrain-Generation) 提供分块、异步网格和多 LOD 思路。项目介绍不足以证明可以修复本项目闪烁，未导入插件或替换世界生成系统。
