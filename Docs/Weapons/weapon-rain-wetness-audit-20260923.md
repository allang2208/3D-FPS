# 枪械雨天湿润效果覆盖审计（2026-09-23）

范围：全部枪械视模与改造配件是否都吃到"下雨变湿"效果。只做代码与资产静态核对，
未启动编辑器、未运行游戏、未做视觉验收。结论均为资源实际绑定与运行时查表逻辑推导所得。

- 复现脚本：`Tools/Weather/audit_weapon_wetness.ps1`
- 本次原始输出：`Saved/weapon-wetness-audit-20260923.txt`
- 本次统计：运行时湿润表解析出 266 条资产路径（含干/湿两侧）；抽查 529 个枪械/配件材质槽，
  348 湿、181 干、134 属有意排除

## 一、结论摘要

**没有全部应用。** 3 把枪本体完全干燥，其余枪械本体基本接入但**配件缺口很大**：
按枪匠在册选项统计，有 10 类配件族整体干燥，且这些选项在 M4/AKM/QBZ191/M16A2/A762 上都可装备。

| 枪械 | 本体 | 已接入湿润的配件位 | 仍然干燥的配件位 |
| --- | --- | --- | --- |
| M4（HK416Replica） | 6/6 湿 | 光学、弹鼓、延长弹匣、垂直/侧倾握把、棱镜阻手器 | 斜角握把、战术消音器、枪口内腔、手电/激光、4 类枪托、均衡/幻影/稳固后握把 |
| AKM（SovietFab） | 1/1 湿 | 光学、弹鼓、延长弹匣（主体槽）、垂直/侧倾握把、棱镜件 | 同上 + 40 发延长弹匣弹匣口 |
| QBZ191 | 6/6 湿 | 光学、手电、激光、均衡/幻影后握把、枪托外多数件 | 枪口内腔、战术消音器、4 类枪托、斜角（共振）握把、稳固后握把 |
| ASH12 | 7/7 湿 | 消音器、颊托、通用配件（含斜角/侧倾/垂直握把） | 无（消音器内腔按设计保留消光） |
| **M16A2** | **0/1 湿** | 自带配件表覆盖大部分配件 | **本体全干**；另加延长弹匣、均衡后握把、枪口内腔、4 类枪托 |
| M1911 | 6/7 湿 | 光学、手电、激光、弹匣/握把/准星/套筒/后座钢件 | `M_M1911_Hero_Ammo`、战术消音器、枪口内腔 |
| DanWesson715 | 3/3 湿 | 聚合物 + Chrome 全组配件 | 无 |
| **A762** | **0/20 湿** | 无 | **全部**（本体 + 全部配件网格） |
| **SVD** | **0/8 湿** | 无配件位（`allowed: []`，只有本体 + 镜） | **全部** |
| PKM | 主体 7/7 湿 | 配件模块本身已接 | 24 个配件网格各剩 1 个接口槽（`M_PKM_QBZ_Body`）；该枪已退役 |

## 二、机制（判定依据）

枪械湿润**不走天气 MPC**，只走一条材质替换路径：

1. `Source/FPSGAME/FPSWeatherManager.cpp:96-97` 固定加载
   `/Game/Weather/RainVisibility/DA_WeatherPresentation`，`:166-167` 传给
   `UWeatherViewEffectsComponent::Initialize`。
2. `Source/FPSGAME/WeatherViewEffectsComponent.cpp:46-90` 把 4 张枪械专属表并入共享表的
   `WetMaterials`：`DanWesson715WeaponAssets::WetMaterialsPath`、`ASH12WeaponAssets::WetMaterialsPath`、
   `PKMLowpolyWeaponAssets::WetMaterialsPath`、`/Game/Weapons/M16A2/UniversalAttachments20260920/DA_M16_AttachmentWetMaterials`；
   再硬编码并入 ExtMagContinuity20260919 三条 dry→wet。
3. `:98-132 BindWeapon` 每 0.2 s 遍历本地角色的 `AKMViewmodel` 及**所有挂在它下面的** `UMeshComponent`
   （`:112-114` 的 `Mesh->IsAttachedTo(Main)`），逐槽用**干材质的 `GetPathName()` 精确匹配**查表
   （`:120-123`，MID 则回退查其 Parent）。
4. `:134-176` 按枪械实例累计 `WeaponWetness`（0..1，受降雨强度与 `GetRainExposure()` 影响、
   停雨后缓慢干燥），并对命中槽的 MID 写 `WeaponWetness` / `WeaponRain` 标量
   （`WeaponRain` 是死参数，见第十节 10.3）。

推论：**查表未命中的槽在任何天气下都不会变湿，且不会有任何日志或报错。**
表里键 = Python `get_path_name()` 的 `"/Game/.../X.X"` 字符串，替换材质必须是
`M_Wet_*` / `*_Wet` 且带 `WeaponWetness` 标量参数。`docs` 中的"材质统一"不等于湿润接入。

## 三、完全干燥的枪械

### 3.1 M16A2（本体）
- 运行网格 `Content/Weapons/M16A2/Gameplay20260919/SK_M16_Manny`，唯一体表材质
  `M16A2Migration/Materials/M_M16A2_PBR`，全表 266 个键中无此路径，也无任何含 `M16A2` 的条目。
- 连带受害：`SM_M16_ext_mag`、`SM_M16_balanced_reargrip` 也绑这个材质 → 同样干燥。
- 讽刺点：M16 的配件表（`DA_M16_AttachmentWetMaterials`）覆盖得很完整，**枪身本体反而漏了**。

### 3.2 A762
- 运行网格 `Content/Weapons/A762/Integrated20260920/SK_A762_Manny`，20 个体表材质
  （`M_A762_Receiver`、`M_A762_Bolt`、`M_A762_Rail`、`M_A762_Handguard03`、`M_A762_UpperReceiver03`、
  `M_A762_FactoryStock_*` 等）**全部无 wet 条目**；全表搜索 `M_A762_` 零命中。
- `A762Attachments::MeshPath` 指向的全部配件网格（`SM_A762_*`、两片折叠机瞄）同样零覆盖。
  A762 是当前唯一"整枪带配件全干"的在役步枪。

### 3.3 SVD
- 运行网格 `Content/Weapons/SVDDragunov20260922/Complete20260923/SK_SVD_Manny`，8 个材质
  （`MI_SVD_Body`、`MI_SVD_ScopeBody`、`MI_SVD_ScopeMount`、`MI_SVD_Magazine`、
  `MI_SVD_ChargingHandle`、`MI_SVD_Trigger`、`MI_SVD_SafetyLever`、`M_SVD_BoltCarrier`）**全部无 wet 条目**；
  全表搜索 `SVDDragunov` / `MI_SVD_` 零命中。SVD 目录（20260922-23）晚于天气表最后修订，属新枪未接入。

## 四、部分干燥

- **M1911**：运行网格是 `Content/Weapons/M1911/RearFinish20260913/SK_M1911_Manny`（不是 Hero 目录）。
  7 个枪械槽中 `M1911/Hero20260913/Materials/M_M1911_Hero_Ammo` 无 wet 条目，其余 6 个湿。
- **AKM 40 发延长弹匣**：`SM_ExtMag_AKM40_Continuous` 与 `SM_ExtMag_AKM40_Mouth` 除
  `M_AKM_Continuous_Graph`（硬编码已接）外还带 `MagazineMouthFinish20260919/M_AKM_MagazineMouth`，该材质干燥。
- **PKM 全部 24 个配件网格**：主体槽已指向 `Finish20/Materials/M_Dry_M_PKM_*`（湿），但配件的接口槽
  仍指向原始 `PKMLowpoly20260922/Bipod07/Materials/M_PKM_QBZ_Body`，而表里只有
  `M_Dry_M_PKM_QBZ_Body_84234a96` 这一份拷贝 → 查表不中。PKM 已按用户判定退役，优先级自定。
- **ASH12 战术消音器内腔** `M_ASH12_TacticalSuppressor_Inner` 干燥——与 `weapon-finish.md`
  "枪口内腔保留消光"一致，视为有意。

## 五、整体干燥的配件族（多为枪匠在册选项）

以下族的**干材质没有任何 wet 条目**，装备后在雨中保持干燥。按 `Content/ColdSteelData/gunsmith.json`
的选项 id 在册，属真实可达路径。目录实测：`ue_m4a1 / ue_akm / ue_qbz191 / ue_m16a2 / ue_a762` 的
option id 均含 `core_stock / qr_performance / skeleton / tactical_telescopic / balanced_reargrip /
phantom_reargrip / stable_antislip_reargrip / tactical_suppressor / brake / titanium_brake / flashlight /
laser / angled_foregrip`；`ue_m1911` 含 `tactical_suppressor / brake / flashlight / laser`；
`ue_pkm_lowpoly` 含上述枪托与后握把族；`ue_svd` 的 `allowed` 为空。

| 配件族 | 受影响枪型 | 干燥材质 |
| --- | --- | --- |
| `TacticalSuppressor20260913/{M4,AKM,QBZ191,M1911}` | 四枪的 `tactical_suppressor` | `M_TacticalSuppressor_Shell`、`_Mount` |
| `M4MuzzlesV1/MI_MuzzleRecess` | M4/AKM/M16/QBZ191/M1911/A762 的 brake/suppressor/titanium_brake 枪口内腔 | `MI_MuzzleRecess` |
| `TacticalDevices20260913/{M4,AKM}/{flashlight,laser}` | M4/AKM 战术手电与激光 | `M_{M4,AKM}_{flashlight,laser}_Body`、`_Collar` |
| `ResonanceGrip20260913/MeshyIntegration/*` | M4/AKM/QBZ191 的 `angled` 前握把 | `M_Resonance_{M4,AKM,QBZ191}` |
| `ReferenceStock5080`（骨架托） | 全枪型 `skeleton` | `M_StockPolymer`、`M_StockRubber` |
| `QRPerformanceStock/Meshy20260913` | 全枪型 `qr_performance` | `M_Stock_Polymer`、`M_Stock_Rubber`、`M_PerformanceStock_*` |
| `CoreStock20260914/Meshy0914005605` | 全枪型 `core_stock` | `M_CoreStock_Rubber`、`M_CoreStock_Body_*`、`M_CoreStock_Adapter_*` |
| `TacticalTelescopicStock20260914` | 全枪型 `tactical_telescopic` | `M_TacticalStock_Polymer`、`_Rubber`、`_Metal_*` |
| `PhantomRearGrip` / `RearGripFinish20260913/{M4,AKM}` | M4/AKM 的 phantom / balanced 后握把 | `M_*_phantom_Body/_Collar`、`M_*_balanced_Body/_Collar` |
| `StableAntiSlipRearGrip/Selected91727` | M4/AKM/QBZ191 的 `stable_antislip_reargrip` | `M_StableAntiSlipRearGrip`、`M_StableGrip_Collar_*` |

两个反例说明这不是"按枪型系统性遗漏"，而是**按批次注册**的结果：

- QBZ191 同款配件是湿的（`M_QBZ191_balanced_Body`、`M_QBZ191_phantom_Body`、
  `M_QBZ191_flashlight_Body`、`M_QBZ191_laser_Body` 均在表内），M4/AKM 同名件却是干的。
- **QBZ191 共振握把实际也是干的**：表里的键写在
  `/Game/Weapons/ResonanceGrip20260913/Repaired91871/QBZ191/M_Resonance_QBZ191`，
  而 `M4AngledForegrip.cpp` 运行时加载的是 `MeshyIntegration/QBZ191/SM_ResonanceGrip`
  → 材质路径不同，注册到了废件上。

## 六、有意排除项（134 槽，非缺陷）

`Tools/Weather/build_natural_weather.py:101` 明确跳过路径含 `manny / armsblack / reticle / lens / glass` 的材质，
`:105-108` 跳过非 Opaque/Masked 及 Substrate（`MP_MATERIAL_ATTRIBUTES`）母材质。因此：

- 共享 Manny 手臂/手套 `M4InfimaV3/MI_Manny_01|02` 在所有枪上都不湿（设计如此）。
- 各瞄具 `M_HoloReticle`、`M_*_Glass`、`M_*_Reticle`、`M_LPVO_Glass` 不湿。
- 枪口内腔 `MI_MuzzleRecess`、`M_TacticalSuppressor_Recess`、`M_SVD_OpticalGlass` 归入此类。
- 715 Chrome 走原生 Substrate Slab，是靠手写表（`DA_DW715_WetMaterials`）绕开该过滤的，属正确做法。

## 七、代码层问题（与内容无关，需单独修）

1. **双持副手枪永不淋湿**（确定性缺陷）
   `Source/FPSGAME/Weapons/PistolDualWieldComponent.cpp:69-71` 把 `DualPistolLeft` 挂在
   `FirstPersonCamera` 上；而 `BindWeapon` 只认 `AKMViewmodel` 及其子孙
   （`WeatherViewEffectsComponent.cpp:112-114`）。副手手枪本体、其镜像配件（`:229` 把
   `Rig->AKMViewmodel` 映射为 `Hands[1].Mesh`，子件随之挂到相机链下）以及左手战术设备的材质
   全部落在过滤之外，雨天保持全干。
2. **验收门槛形同虚设**，这是上述内容缺口长期未被发现的原因
   - `WeatherPresentationValidation.cpp:103`：`Check(Bindings>=1, ...)` —— 只要≥1 个槽命中就算通过，
     0/1 槽的 M16 与 6/6 槽的 M4 无法区分。
   - `:143`：`GetWeaponWetness()<.01f && GetWetMaterialCount()>0` —— 只要求"有绑定"，不要求覆盖完整。
   - `:158`：只校验绑定数量前后一致（不泄漏），与覆盖率无关。
3. **注册表靠硬编码路径，且静默失败**
   `WeatherViewEffectsComponent.cpp:52-77` 把 4 张表 + 1 条内联路径 + 3 条 ExtMag 写死在 C++ 里。
   新增枪械（A762、SVD）或新增配件族时，既没有表也没有校验，`LoadObject` 失败只让该枪回落到"全干"。
4. **共享构建脚本的两个坑**
   - `Tools/Weather/build_natural_weather.py:127` 的目录清单写了 `M4Muzzle`，实际资产目录是
     `M4MuzzlesV1`；`get_assets_by_path` 对不存在的路径返回空集且不报错，于是 `MI_MuzzleRecess`
     从未被自动注册。这正是第五节枪口内腔缺口的来源。
   - 同一清单是 2026-09-12 的快照，不含 TacticalDevices、TacticalSuppressor20260913、
     CoreStock/QR/骨架/伸缩托、后握把族、共振握把、ExtMag 等后来新增目录；脚本没有任何
     "目录不存在/覆盖率"断言，因此共享表无法随枪匠目录一起成长。
5. **合并顺序会静默覆盖**
   `Initialize` 用 `Assets->WetMaterials.Add(Key,Value)` 顺序并入，同键后者覆盖前者。当前
   `M_Prism_Polymer` 的 wet 值是 ASH12 专用的 `M_ASH12_M_Prism_Polymer_Wet`，也被 M4/AKM/QBZ191/M16/PKM
   的棱镜阻手器共用。因为干材质是同一个资产，观感差异有限，但这条耦合没有任何注释或断言保护。
6. **换枪/换配件后有 ≤0.2 s 的干燥窗口**
   枪匠流程会 `EmptyOverrideMaterials()`，绑定循环 `BindCountdown=.2f` 下个周期才补回。
   低优先级；若要消掉，可在换枪/换配件末尾主动触发一次 `BindWeapon`。
7. `WeatherPresentationValidation.cpp:54-55,61-62` 直接解引用
   `FindConsoleVariable(...)->Set(...)`，未判空。当前两个 CVar 是静态注册，暂无风险；改名或裁剪模块会崩。
   （2026-09-23 已修：改为 `SetWeatherCVar()` 带判空与告警。）

## 八、复现

```powershell
pwsh -File Tools/Weather/audit_weapon_wetness.ps1            # 分组报告
pwsh -File Tools/Weather/audit_weapon_wetness.ps1 -OnlyDry   # 仅未覆盖项
```

脚本只用文件读取：解析 5 张运行时湿润表的对象路径键，再按各 `*Attachments.h` /
`M4*Visual.cpp` / `SkeletonStockVisual.cpp` / `PhantomRearGripVisual.cpp` 解析出的运行目录，
枚举网格资产并逐个材质槽判定 `WET / DRY / INTENTIONAL`。`-SkipPaths` 里记录了被淘汰的同级目录
（如 `CoreStock20260914/{AKM,M4,QBZ191}` 与运行时 `Meshy0914005605`），避免报告被废件淹没。
它是资产内容检查，不能替代实机画面验收。

## 九、修复建议（本次未实施）

1. 先把第五节表格里的配件族按各自枪身补 dry→wet（照 `weapon-finish.md` 的"以当前枪身为基准"），
   优先顺序建议：战术消音器 → 手电/激光 → 斜角握把（含修正 QBZ191 的注册路径）→ 四类枪托 → 后握把族。
2. A762、SVD、M16A2 本体各建 `DA_*_WetMaterials` 并按现有四表模式并入 `Initialize`；
   三者各自只需 1～20 个材质，量最小、观感改善最大。
3. 修 `Weapons/PistolDualWieldComponent.cpp` 的副手挂点，或在 `BindWeapon` 中把
   "挂在相机下的持械网格"纳入绑定范围，二选一；双持副手是当前唯一"结构上不可能变湿"的路径。
4. 把 `WeatherPresentationValidation.cpp:103` 改成逐枪断言覆盖率（例如：当前视模除有意排除项外
   湿槽比例 = 100%），让审计脚本的结论可以在实机自动复现。
5. 修 `build_natural_weather.py:127` 的 `M4Muzzle`→`M4MuzzlesV1`，并把目录清单改为从枪匠目录
   （`gunsmith.json` 的 option id）推导，或在构建末尾对"未注册的枪械/配件目录"直接失败。

## 十、性能负担排查（同日追加）

结论一句话：**每帧 CPU 开销不大，真正的负担不在"每帧写参数"，而在两处——一处 100% 无效的参数写入把
枪械湿润的参数流量直接翻倍；以及 120 个重复母材质带来的 shader map / PSO / 加载开销。GPU 侧基本无负担**
（不增加 draw call，水滴是纯 ALU）。

判定方法遵循项目 `skills/ue5-performance-packaging/references/frame-budget-stat-semantics.md`：
**数每秒调用了多少次昂贵 setter**，而不是编造毫秒。

### 10.1 一次 `SetScalarParameterValue` 到底做了什么（UE 5.8 源码核对）

`UMaterialInstanceDynamic::SetScalarParameterValue`
→ `Engine/.../MaterialInstance.cpp:4240-4281`：

1. `GameThread_FindParameterByName` 线性查参数名；**值没变就直接返回**（唯一守卫）。
2. 值变了才入队一条 render command → `:625-630`：`RenderThread_UpdateParameter` + **`CacheUniformExpressions`**。
3. `MaterialRenderProxy.cpp:651-678`：把自己加进 `DeferredUniformExpressionCacheRequests`（**TSet，按 proxy 去重**），
   然后 `InvalidateUniformExpressionCache`（`:695-736`）——里面有两个**全局同步点**：
   `GUniformExpressionCacheAsyncUpdateTask.Wait()` 与 `FRDGBuilder::WaitForAsyncExecuteTask()`，
   外加互斥锁、VT/材质缓存回调清理、逐 feature level 作废 `CachedUniformExpressionShaderMap`。
4. 真正的重算每帧对每个 proxy 只做一次（`GDeferUniformExpressionCaching=1`，
   `MaterialRenderProxy.cpp:906-981`），带 CSV 计时器 `Material_UpdateDeferredCachedUniformExpressions`（`:932`）。

即：**每次写入 = 一次线性查找 + 一次入队 + 一次含两个全局 wait 的失效**；不是"每写一次就重编材质"，
但也绝不是免费。这类 setter 不属于 `frame-budget-stat-semantics.md` 里点名的那批"重建渲染状态"的 setter，
不应与之等同，但它在渲染线程上引入了同步点。

### 10.2 系统各处的写入频率

| 来源 | 每次写入 | 频率 | 说明 |
| --- | --- | --- | --- |
| 枪械湿润 | 2 个标量/绑定 | **每帧** | 只在值变化时真正入队；稳态趋近 0 |
| 屏幕雨滴 MID | 3 个标量 | 每帧 | `ScreenWetness` 干燥尾 32 s |
| 雨湿地贴池 | 16 patch × 2 标量 | **10 Hz** | `WeatherSurfaceComponent` 构造函数里 `TickInterval=.1f` |
| 丘陵地面 MID | 1 个标量 | 每帧 | `TemperateHillsWorld.cpp:559` |
| 天气 MPC | 3 个标量 | 每帧 | MPC 是集合级更新，不走 per-MID 失效，单价低得多 |

枪械绑定数的**实测值**：`WEATHER_PRESENTATION_AUDIT_PASS failures=0 … materials=8`
（`Saved/WeatherPresentation20260912/*/runtime.log`，2026-09-12，当时是一把未满配的 M4）。
按本报告第一节，满配且全部命中湿润表的 M4 是：本体 6 + 全息 1 + 枪口 2 + 弹鼓 2 + 阻手器 2 + 垂直握把 1 = **14 槽**。

于是枪械路径峰值约 **2 × 14 × 60 = 1680 次/秒**，是全系统最大的一项
（雨湿地贴 320/s、屏幕 180/s、地面 60/s、MPC 180/s）。

**时间窗**：写入只发生在过渡期——淋湿约 15 s（`Rain*0.065`/s 到 1.0），停雨后干燥 120 s（`Delta/120`）。
稳定暴雨里 `Rain` 与 wetness 都饱和不变，引擎的值守卫把写入降到接近 0。
所以它是**突发型**开销，不是每帧恒定负担。

### 10.3 已确认的浪费：`WeaponRain` 无人消费（100% 死写）

- `WeatherViewEffectsComponent.cpp:166` 每帧写 `B.Wet->SetScalarParameterValue(TEXT("WeaponRain"),Rain)`。
- 全项目检索 `WeaponRain` **只出现在这一行**：任何 HLSL、导入脚本、材质里都没有。
- 二进制核对：**157 个 `M_Wet_*` 母材质中 0 个声明 `WeaponRain`**（`WeaponWetness` 是 157/157 全有）。
- 后果比"写了个没人读的值"更重：MID 找不到同名参数时会**新建条目并强制更新**
  （`MaterialInstance.cpp:4247-4254`，`bForceUpdate=true` 直接跳过值守卫），
  所以这个不存在的参数每帧都真实入队，并触发 10.1 的失效路径。

**净效果：枪械湿润的参数入队数、失效次数与 proxy 重算次数全部翻倍，且这部分永远不会因稳态而降为 0。**
（`WeaponWetness` 本身没问题：157 个湿母材质全部声明了它。）

修法：删掉这一行；或先让 `WeaponBeads.hlsl` 真正用上"雨量"再写。

### 10.4 资产 / 加载 / PSO 负担（比每帧 CPU 更实）

- 运行时 5 张表共引用 **255 个湿润材质**（6.7 MB uasset），其中 **120 个是重复母材质 `M_Wet_*`**：
  每个都是独立 `UMaterial`，各自一份 shader map 与 PSO 集合。母材质由 `duplicate_asset` 复制，
  **继承原件全部 usage**，再显式加 `MATUSAGE_SkeletalMesh`，因此被这套湿润体系覆盖的枪械材质，
  其材质/排列/PSO 足迹大致翻倍。
- `FPSWeatherManager.cpp:166` 在 `BeginPlay` 用 **`LoadSynchronous()`** 加载这张 DA →
  255 个材质及其 shader map 在游戏线程一次性拉起。这是启动期一次性成本，不是每帧成本，但会加进首帧/读图时间。
- `Config/DefaultEngine.ini` 已开 `r.PSOPrecaching=1`，首次渲染的 PSO 创建被摊到后台；
  但 cook 体积、shader map 内存与 precache 工作量仍随材质数线性增长。
- **向前看**：若按第九节把缺的配件族补齐，湿润材质数会继续上升（粗估 +80～120），
  shader/PSO 足迹与参数写入量会同向增长——**所以参数路径该在补覆盖之前或同时优化**，
  尤其 10.3 那行删掉等于白拿一半。

### 10.5 GPU 侧

- **不增加 draw call**：湿润材质是"替换槽位材质"，一个槽位本来就一次 draw，绑定前后 draw 数不变。
- 枪身水滴 `SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl`：2 层，每层约 55–60 条标量运算，
  **无贴图采样、无导数、无额外 pass**。按 1440p、枪身占屏 ~25% 估算约 1e8 标量运算/帧，
  在现代 GPU 上属零头；主要影响是像素着色器变长带来的寄存器压力。
- 这套系统里 GPU 最贵的一件不是枪身，而是**同一组件的屏幕雨滴后处理** `M_ScreenEdgeRain`：
  整屏 pass 且带 `SceneTextureLookup` 依赖取样。已用 `guard`（只做外圈）与
  `if(strength<.0001 || Wet<.0001) return Scene.rgb;` 早退遮罩，调参时优先看它。

### 10.6 建议（2026-09-23 已实施 1/2/3/5，未实施 4）

`Source/FPSGAME/WeatherViewEffectsComponent.{h,cpp}` 与 `WeatherPresentationValidation.cpp`，
构建通过（`Saved/BuildEditor/build-20260923-123931.log`），实机未测。

1. **已实施：删掉 `WeaponRain` 死写。** 该参数在 157 个湿母材质里 0 个声明，写入是纯浪费。
   同时把 4 个仍在用的参数名提为 `FName` 静态常量，去掉每次写的 `TEXT()` 构造与名字比较。
2. **已实施：量化守卫（1/255 步进）。** 每个绑定记录 `LastPushed`，只有量化值变化才真正写；
   归零时只写一次 0。120 s 干燥尾从约 7200 次/绑定降到 ≤255 次，稳态为 0。
   屏幕雨滴 MID 的 3 个参数与 `PostProcess->BlendWeight` 同样加了变化守卫
   （`BlendWeight` 在引擎里是普通 UPROPERTY，直接赋值即可）。
3. **已实施：每秒写入计数器。** `TickComponent` 累计"实际写入 / 被守卫吸收"，每秒输出一条
   `WEATHER_WET_WRITES perSec=… skippedPerSec=… bindings=… wet=… screen=…`（有写入才打印）。
   验收判据：稳定暴雨且湿饱和时 `perSec` 应为 0。
5. **已实施：绑定路径复用。** `Initialize` 把共享表的 `FString` 键重建成 `TMap<FName,…>`，
   `BindWeapon` 不再每 0.2 s 对每个槽位 `GetPathName()` 分配字符串；
   新增 `SharedWet` 池，MID 按"原材质"复用（同一材质多处槽位共用一个 MID），
   枪匠反复改配件不再持续 `Create` 出等待 GC 的 MID。
   另外把失效绑定剪除从 0.2 s 一次改为每帧一次（只遍历已有绑定，代价可忽略），
   发现被剪除立刻补扫，换枪/换配件的干燥窗从 ≤200 ms 缩到一个 tick。
4. **未实施：`WeaponWetness` 改走 `MPC_FPS_Weather` 集合参数。** 需要重做湿母材质模板并重跑
   `build_natural_weather.py`，涉及资产批量重建，超出本次代码修复范围。

### 10.7 怎么量（不要用单次 A/B）

按 `frame-budget-stat-semantics.md`：同一构建、同一位置、关闭串流/虚拟显示层，跑 2–5 次取中位数；
同构建相隔两分钟的两次测量可以差 3 倍，单次 A/B 结论无效。

- 开关对比：`fps.WeaponWetness 0` ↔ `1`（定义在 `WeatherViewEffectsComponent.cpp:22`）
- `stat unit` / `stat unitgraph`（只作趋势；`Game`、`Draw` 不可相加、不可跨口径相减）、`stat GPU`、`stat SceneRendering`
- CSV：`-csvCaptureFrames=600`，重点看 `Material_UpdateDeferredCachedUniformExpressions`（源码 `MaterialRenderProxy.cpp:932`）与渲染线程行
- 内存：`-LLM` / `stat LLM` 看 `MaterialInstance` tag（`SetScalarParameterValue` 内部就有 `LLM_SCOPE(ELLMTag::MaterialInstance)`）
- 预期：稳定暴雨且 wetness 已饱和时应接近 0 写入；若读数持续几十次/秒，说明守卫或量化没生效

## 十一、状态

- 已完成：静态代码审计、运行时湿润表解析、逐枪逐槽覆盖判定、可复现审计脚本；
  第十节的性能路径排查（引擎 5.8 源码核对 + 项目自有日志中的实测绑定数 + 资产足迹统计）；
  **以及第十节 10.6 的 1/2/3/5 与第七节第 7 项的代码修复，编辑器模块构建通过**。
- 未做：资产改动（`MPC` 化 wetness 需重做湿母材质）、编辑器接入、PIE 截图、实机视觉与性能实测。
  修复改动未经实机验证，验收按 10.7：`fps.WeaponWetness 0/1` 对比、`WEATHER_WET_WRITES`
  日志在稳态应接近 0、跑 2–5 次取中位数。
