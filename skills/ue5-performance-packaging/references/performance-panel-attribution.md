# 性能面板：采样口径与归因

用于 UE 性能导出分析、面板可靠性修复及主场景优化。采样或运行验收仅在用户要求时执行；已有 JSON 和本机引擎源码可用于离线分析。

## 时间与观察范围

- Slate.WindowPaint 内可能嵌套游戏 HUD NativeTick。2026-09-23 地牢案例通过 trace 才将周期性慢帧归到 HUD；看到窗口 Paint 高不能直接归咎编辑器外壳，看到光追／VSM 警告也不能跳过 CPU 归因。已有明确热点时，开发约束见 [高频路径与资源预算](fpsgame-performance-development.md)。

- 先确认 schema、地图、运行模式、相机、分辨率、质量设置、样本窗口和暂停/后台状态。不同 session 或视角的数据不能直接宣称为优化前后收益。
- 用单调时钟将 CPU scope 与帧区间裁剪后关联；父子 scope 不重复求和。没有来源帧 ID 的 Game/Draw/GPU 发布读数保留各自分布，不自行平移来制造逐帧对应。
- `Slate.TickAndDrawWidgets` 是进程级区间，可能包含其他编辑器窗口、布局、绘制和缓冲等待。`Slate.WindowPaint` 只覆盖窗口 Paint；两者之差不能直接命名为等待。性能页刷新一次的耗时也不是每帧耗时。
- 冻结面板后，分别保存快照采集时和导出点击时的页签、显示/冻结、刷新周期和模糊配置；时点配置不代表整个采样窗口始终相同。
- 记录事件的 epoch、容量和丢弃情况。GC 区间、同步加载包和 async loading flush 起点可补空白；只有起点的事件不是加载耗时，未采集的空白仍明确未归因。

## 几何与灯光

- `ForcedLodModel=0` 表示自动，正值表示 `LOD 索引 + 1`；强制 LOD1 使用 2，资产至少有两个 LOD。导出原值、解释索引、MinLOD 与覆盖标志；实际渲染 LOD 未取得时用 null。
- 源 LOD 面数、组件数、实例数、材质槽和相对复杂度均不是实际提交面数或 draw calls。按资产聚合在 Top N 截断前完成，说明视锥候选与实际遮挡可见的区别。
- SkyLight 不属于普通 `ULightComponent` 统计，需独立收集。实时捕获开关不是本帧捕获次数；启用灯数量也不能替代 Lumen/VSM/雾的 GPU 分项。
- GPU pass、真实屏幕比例、线程/GPU 对齐或内存预算未取得时明确缺失，不用默认值补成实测，也不因此直接全局降画质。

## 修复次序

先修确定的配置错误与同步阻塞，再处理已归因的重复工作，最后对仍未归因的区间补采样入口。图标管线见 [运行时图标准备](../../ue5-ui-umg-slate/references/runtime-icon-pipeline.md)；几何制作见 [静态构件实例化](../../ue5-pcg-building/references/static-mesh-instance-production.md)。

FPSGAME 案例：`Docs/Performance/main-scene-export-analysis-20260923.md`、`main-scene-optimization-20260923.md`；源码入口为 `FPSPerformanceMetrics*`、`FPSPerformancePhases.cpp`。历史构建/资产保存记录不代表后续已复测或稳定 60 FPS。

## 怪群短时卡顿与自动采样

- 区分同步生成、随后 AI/移动、CPU 动画与 GPU Morph/蒙皮。SpawnActor 调用耗时不包含延迟的渲染工作；预热不能代替每帧高耗时的治理。新一轮 CPU/GPU 主导关系可改变，不用旧显存报警推断新样本。
- 对同次刷怪前、低帧、恢复段记录 CPU scope 调用数与包含/独占时间；同时覆盖游戏线程、导航/动画后台任务及 GPU 队列。共享 morph 输入按资产去重，活动曲线数或顶点数不能冒充 GPU 耗时。
- 自动采样触发正式激活事件，排除尚未 BeginPlay 的准备实例；保留足够尾段。Python 回调间隔不是帧时间。先读 capture 状态、错误与实际区间，再解释 trace；armed 或大 trace 文件不等于完整战斗样本。
- UE Python 以实际反射接口为准：此项目 UE 5.8 的 Controller 使用 get_controlled_pawn，原生 GetPawn 不对应 get_pawn。可选 AI 状态读取失败应单独标记缺失，不能丢掉原生 CPU/GPU 追踪；修订后也须确认完整采样再宣称可用。
- 在测量窗口内避免重型 RHI 资源全量枚举与 JSON 场景扫描。复用至多 2 Hz 的被动观察，停止 trace 后导出；诊断开关恢复原值。trace 中断但游戏仍活着时，先救回 F6 独立战斗窗口，不把它冒充逐函数 trace。
- 玩家暂缓优化时记录未解问题、最后有效证据、待验证修订和恢复入口；不继续采样。FPSGAME 案例：Docs/Performance/monster-attribution-and-preview-crash-20261013.txt。
