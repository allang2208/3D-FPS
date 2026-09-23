# 地牢性能导出分析（2026-09-23 18:13）

> 以下为优化前的历史排查；后续采样已将主要慢帧定位到 HUD，相关制作和用户改善反馈见 [优化完成记录](dungeon-performance-completion-20260923.md)。本文的“当前”指当时导出，不代表后续资产状态。

范围：按用户要求阅读性能 skill、截图、既有 JSON、当前源码、导入脚本及同次运行日志，分析优化空间。本轮仅新增本文，没有修改源码、配置或资产，没有打开/重启 UE，也没有启动游戏、运行测试或采集新数据。

## 数据与适用范围

- 导出：`Saved/PerformanceReports/performance-20260923-101329-9E8BBC634CB54ED8F55C04A395B62ED9.json`，schema 9，采集于北京时间 18:13:28.717。
- 地图：PIE `L_Dungeon_Randomized`；2552×1222；种子 2064575536。ScreenPercentage=0 是配置读数，不能当成实测渲染比例。
- 相机 Z=-184499.25 cm；最近地牢灯距相机约 1856 m；网格视锥候选与灯光候选均为 0。用户已确认导出时掉出地图/黑屏。这不是正常房间内游戏的 GPU 性能基线，也不能证明 GPU 没有瓶颈。
- 130 帧覆盖 10.0281 秒，其中 17 个后台帧合计约 5.6665 秒，平均 333.3 ms。窗口 12.96 FPS 混入显著后台节流，不能直接当作地牢正常帧率。
- 113 个前台标记帧合计 4.3616 秒，帧时间平均 38.60 ms、中位数 45.99 ms、P95 64.55 ms。包含一个从后台切回的 332.47 ms 边界帧，不人为移除后宣称正常游戏结果。
- 采集/导出时性能面板均打开，页签索引 3，刷新间隔 500 ms，模糊强度 9、半径 21；这两个时点不能代表整个窗口始终处于相同 UI 状态。

## 已记录的耗时

以下 CPU scope 按单调时间与前台帧区间取交集；父子区间不能相加。GPU/线程发布值无来源帧 ID，分别统计，不与 CPU scope 逐帧硬对齐。

| 项目 | 前台帧平均 | 解释 |
| --- | ---: | --- |
| Slate.WindowPaint | 25.89 ms | 全部记录指向 `FPSGAME - 虚幻编辑器` 主窗口；包含窗口内各界面，尚未分到具体控件 |
| Slate.TickAndDrawWidgets | 26.93 ms | 包含 WindowPaint，不能重复求和 |
| World.Tick | 5.98 ms | 当前世界 Tick，不等于整个游戏线程 |
| GPU0 发布读数 | 5.98 ms | 延迟且未对齐，视角已掉出地图，不代表地牢内部渲染 |
| Dungeon.RoomLighting | 0.0118 ms/前台帧 | 调度 CPU 开销很小，不是灯光 GPU 成本 |

窗口内快照事件峰值约 6.39 ms，面板内容更新峰值约 5.47 ms，均只观察到 2 次事件。不能将其误解为每帧 25.9 ms 的来源。WindowPaint 在部分连续帧交替出现约 0.7–1 ms 和 36–39 ms，也有约 50–69 ms 的事件；目前没有具体控件级证据，不能直接断定是面板模糊、HUD 或某个编辑器面板。

图标子阶段本次单事件峰值低于 1 ms；积液伤害与灯光调度 CPU 事件也很小。没有证据优先重写这些玩法逻辑。

## 优化顺序与具体入口

### 1. 补齐新增网格的 Nanite/LOD，并统一后续导入策略

源几何按组件实例累计为 22,182,133 三角形，其中 `_Tiles` 为 12,337,903，约 55.6%。这是资产 LOD0/fallback 总量，不是同屏实际提交面数。

当前 Top 20 组件全部报告无有效 Nanite 数据、单个 LOD、开启投影。重点包括：

| 资产 | 每件源三角形 | 已记录组件数 |
| --- | ---: | ---: |
| SM_RS_BossPumpHall_Tiles | 841,008 | 1 |
| SM_RS_Drainage_CombatDoor_Tiles | 520,373 | 3 |
| SM_RS_FreightTransfer_Tiles | 511,905 | 3 |
| SM_GoddessStatue_Diana | 500,696 | 1 |
| SM_RS_VentilationLoop_Tiles | 454,922 | 2 |
| SM_RS_Distribution_CombatDoor_Tiles | 401,577 | 7 |
| SM_RS_BossPumpHall_GalleryRails | 379,420 | 1 |

旧优化回执保存了 79 个网格，但上述 Top 20 涉及的 9 种资产均不在旧 `saved_meshes` 清单中。主要问题是新增资产覆盖不完整，不能将旧回执的 remaining=0 解读为当前全部资产已优化，也不能据此断言这 9 种曾优化后被回退。

另有明确导入风险：

- `SourceAssets/DungeonUnderground20260923/Scripts/import_assets.py:33` 明确设置 `settings.enabled=False`。
- `SourceAssets/DungeonGoddessStatue20260922/Scripts/import_diana.py:195` 明确关闭 Nanite。
- RouteRepairs 复用 RoomShells 的导入器；它保留已有设置，但不能自动为所有新增资产启用 Nanite。
- `SourceAssets/DungeonPerformance20260922/Scripts/optimize_assets.py:106` 仅凭旧回执跳过资产，不能覆盖“回执存在但后来资产已重新导入”的情况。建议改为以实际资产设置/构建结果和源版本判断是否需要处理。

建议：对材质兼容的刚性构件建立并保存有效 Nanite 数据；不支持者补真实 LOD 链；统一导入器保留/应用策略。保留近景瓷砖、破损边缘、栏杆轮廓和既有玩法碰撞。单纯把 Nanite 开关写成 true 并不等于当前运行资产已经具有有效数据。

截图中的非 Nanite VSM 队列警告与该资产配置吻合，但尚无房间内 GPU pass 数据，不能量化它占了多少毫秒。Epic 同样建议可支持的几何使用 Nanite，非 Nanite 几何建立完整 LOD 链：[Virtual Shadow Maps](https://dev.epicgames.com/documentation/unreal-engine/virtual-shadow-maps-in-unreal-engine)。

### 2. 光追几何单独减负，避免只提高预算

截图：always resident 606.145 MiB、requested 617.06 MiB，预算 400 MiB。第二项已超预算约 217 MiB。“exceeds 20%”是常驻比例警告阈值，不代表仅超预算 20%。本机引擎 `Engine/Source/Runtime/Engine/Private/Rendering/RayTracingGeometryManager.cpp` 中预算默认 400，警告判断与此一致。

当前导出为 Lumen HardwareRayTracing=1，RayTracing.Shadows=0；关闭光追阴影不等于关闭 Lumen 使用的光追几何。

旧优化脚本保留 100% fallback 几何、误差 0，主要为了保留碰撞和细节；这不能保证光追几何同步变轻。建议补独立光追代理/LOD，按实际使用资源控制高面数常驻几何。项目已设置 `r.RayTracing.RayTracingProxies.ProjectEnabled=True`，但这不能证明每个资产都已生成代理；导出也未提供代理实测数据。

不能直接把所有 fallback 几何删掉或大幅简化：多个地牢导入器使用 `CTF_USE_COMPLEX_AS_SIMPLE`，地板、台阶、门洞的行走与弹道碰撞必须保留。适合拆分渲染、光追和导航表示后分别控制复杂度。

依据：[Epic Ray Tracing Performance Guide](https://dev.epicgames.com/documentation/unreal-engine/ray-tracing-performance-guide-in-unreal-engine) 说明无 LOD 网格可能永久驻留，并介绍 Ray Tracing Proxies 与几何池软预算。

### 3. 减少装饰几何参与导航，扩大兼容构件实例化

同次日志 `Saved/Logs/FPSGAME.log` 的 10:11:05–10:11:24 UTC 多次报告导航碰撞导出过重：约 22.7–50.1 万三角形/组件，包括雕像和大厅/楼梯构件。该证据主要指向进入地牢、导航准备期间的资源和构建成本，不足以证明它们每帧都在重建。

建议：装饰电缆、无行走用途的细栏杆与雕像细节使用简化导航表示或关闭导航参与；用必要的简单阻挡保留怪物避障。地面、台阶、桥面、门洞按实际形状保留，不能直接统一禁用碰撞/导航或用房间大盒子封住通道。

本次生成 659 个部件，只有 20 个实例进入 8 组，627 个独立刚性部件。生成器的实例化路径要求有效 Nanite 数据，因此补齐该数据后可进一步归并兼容重复构件。收益需要实际可归组数量决定；组件数下降不等于 draw call 等量下降。

生成记录 elapsed 27.26 秒、布局工作线程 526 ms、最慢装配批次 21.68 ms；elapsed 包含分帧等待及其他阶段，不能直接说 CPU 连续阻塞 27 秒。

### 4. 纹理池与资源驻留按实际需求分配

截图显示纹理流送池超预算约 1.364 GiB。同次启动日志明确记录 `r.Streaming.PoolSize=1000`，后续 `Texture pool size now 1000 MB`。因此不能把该提示直接解释为整张显卡显存已经耗尽。

建议顺序：定位地牢高占用贴图、NeverStream/缺 mip 资源与不必要的整套引用，按实际屏幕尺寸制定纹理分辨率和 mip 策略，再结合编辑器、RT、VSM、渲染目标共同占用设置合理池预算。现有 JSON 没有逐贴图内存或真实剩余显存，不指定未经依据的固定 4 GB/8 GB 预算。

纹理池与光追几何池是不同预算，扩大一个不会修复另一个。依据：[Epic Texture Streaming Configuration](https://dev.epicgames.com/documentation/en-us/unreal-engine/texture-streaming-configuration-in-unreal-engine)。

### 5. 单独处理编辑器/UI 绘制开销，保留已有房间灯光分级

本次直接测得的前台 CPU 大项是编辑器主窗口 Paint，尚不能归给某个游戏控件。下一步可进一步定位窗口内布局/绘制，随后针对已归因部分做失效缓存、静态内容缓存、增量更新和隐藏页面停更；当前没有依据先重写 HUD 或关闭玻璃效果。

灯光总计 158，启用 153，开启投影标志 145，但实际提交数未知。不能说有 145 盏灯在该黑屏帧同时渲染。Optimize 与 RoomCulling 已为 1；当前相机在房间范围外，`AuthoredDungeonLighting.cpp` 明确保留全部 Wanted，交由原生显示距离处理。这解释了全局启用数量，不能据此断言房间裁剪完全未接入。

正常房间内仍可沿现有主灯/补光策略细化重叠范围、装饰投影及相邻房间保留范围。阴影和 Lumen 的真实优先级需房内 GPU 分项，暂不全局降画质。

## 边界与后续所需数据

掉出地图是独立的碰撞/位置问题，应先解决才能获得代表性行走采样。本轮没有将其擅自扩展成代码修复。当前资料无法确定掉落起点和具体失效构件。

下一份有效资料应来自未掉落的正常房间内、前台连续操作的采样，保留种子/视角/分辨率；正常游戏与打开性能面板分别记录。GPU pass、纹理列表和光追几何驻留数据能进一步排序上述候选。本轮没有执行这些采样或测试，也不承诺具体 FPS 增益。
