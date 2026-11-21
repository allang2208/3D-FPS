---
name: ue5-performance-packaging
description: UE5.6-UE5.8 performance budgeting, regression diagnosis, and packaging readiness. Use for FPSGAME hot-path, HUD, asset or streaming performance constraints, frame-time analysis, PIE performance work, and packaging readiness.
---

## 执行约定

**第一条（FPSGAME）　文件位置与引用路径。** 以含 `FPSGAME.uproject` 的当前工程根为准，先读 `Docs/Production/README.md` 和 `WORKFLOW.md` 第 4.1 节。先确定制作源、正式资产和输出目录，再创建或引入文件。工程 Content 资产用 `/Game/...` 包名引用，制作脚本从工程根或已配置的制作源根解析相对路径。交付时在同一功能条目登记实际位置、引用及备份状态。

遵守用户全局规则：后台制作、不主动测试、不跨对话协调。涉及 UE 构建或资产操作时，按需读取[后台开发与接入规则](../ue5-auto-assistant/references/editor-open-development.md)；已读则复用。 原因：制作授权不包含额外运行或验收，交付应保留未测试的实际状态。

## FPSGAME 性能开发约束（2026-09-23）

贴身袖口模拟、内衬穿模及换装卡顿，参考 [锁子甲同步摆动案例](../ue5-fps-arms-animation/references/chainmail-surface-and-secondary-motion.md#4-巫婆布料哪些可复用哪些不应照搬)。代理粒子数不代表完整开销；区分骨骼映射错误、初始化、求解和材质成本，小幅衣缘可用共享有界位移场。没有同场景实测，不把结构简化换算成帧率收益。

新增模型预算、第一人称装备面数及减面必要性，读 [按用途分配面数](../asset-model-workflow/references/geometry-budgets-by-use.md)：高模、游戏 LOD0、可见组合和帧时间分别统计；复杂近景物体允许超出初始区间。当前钢甲 14.4 万面不要求强制减到 6–8 万；材质采样、蒙皮、纹理和同屏数量共同决定成本，没有实测不把候选减面写成必要优化或帧率收益。 原因：成本取决于实际可见量与变形和材质路径，统一面数阈值会损伤近景质量。

功能开发涉及高频刷新、属性查询、场景生成、资源加载或图标时，先按改动范围读取 [FPSGAME 性能开发约束](references/fpsgame-performance-development.md)。把更新触发、重复工作和资源预算纳入实现，不等出现掉帧后再补；此入口不自动启动采样、测试或打包检查。 原因：制作授权不包含额外运行或验收，交付应保留未测试的实际状态。

几何密度、大面积构件与 LOD 方案另见 [场景几何成本与 LOD 收敛](references/scene-geometry-cost-and-lod.md)。按实际遮挡与观察距离处理，不机械强制 LOD 或按“地板”命名关闭阴影。

天空 HDR 常驻显存、BC6H 压缩或间歇性持枪低清，读取 [HDR 与纹理驻留](references/hdr-texture-residency.md)，注意诊断命令可能推进流送。

# Quick Start

- PIE、原工程与独立包性能对照，或资源不全/无怪但帧率更高时，先读 [正式战斗负载与性能基线](references/runtime-baseline-equivalence.md)。构建成功和局部资源覆盖不证明场景等价。

- 地牢选中路线异步准备、共享 ISM 房间可见性和取消回滚，读取 [地牢房间资源准备](references/dungeon-room-streaming.md)；异步加载、隐藏和卸载是不同操作。

- 启动前完整预加载、两档加载与纹理池准备，读取 [进入场景前的资源准备](references/entry-resource-preparation.md)，区分结构就绪、材质/纹理就绪和有限显存预算。
## 按任务区分制作、采样与打包

- 普通开发只把已有性能约束落实到改动路径；采样、依赖审计、打包试跑和回归须有用户对应要求。原因：引用性能技能不意味着允许新增整项目验证工作。
- 用户要求性能分析时，使用现有证据并记录地图、镜头、负载、画质、运行模式、硬件和时间窗口；缺项明确说明。原因：这些条件变化都会改变帧时间，不能用不等价场景归因优化收益。
- 比较中位数、分位数和所用单位，区分用户反馈、单帧峰值与可重复测量。原因：偶发峰值与平均成本不同，主观顺畅不能直接换算为毫秒收益。
- Game 与 Draw 不相加，CriticalPath 中的等待不直接算作 GPU 执行；具体口径读[帧预算统计](references/frame-budget-stat-semantics.md)。原因：线程工作存在重叠和依赖，错误相加会夸大瓶颈。
- 定位以采集能够归属的系统为限，不把 setter 调用次数或总帧时间写成某组件/图元的实测耗时。原因：调用数量和耗时是不同证据，统计面板未必提供逐对象计时。
- 局部功能引入第二套地形或流送系统时，先读取现有生成、碰撞和更新范围；只在用户要求采样时做对照。原因：两个后端可能竞争相同线程、显存和碰撞预算，不能仅按新增功能的尺寸推断成本。
- 打包任务沿用目标配置、地图与 cook 清单，必要构建读取真实返回码和首个失败依赖。原因：批处理调用方式可能丢失退出码，后续连锁错误不能替代首个失败原因。
- 缺包、缺 Skeleton 或动画 hash 断言按该次日志定位依赖，保留原路径及合法素材来源；不删除 AlwaysCook 项掩盖缺失。原因：删掉 cook 入口可能只让错误消失，却使发布包缺少需要的资源。
- 不把一次 Skeleton 缺失案例推广为所有 `!Hash.IsZero()` 断言的唯一根因，也不机械重复失败 cook。原因：相同断言可以有不同上游输入，重试前需要处理已知失败条件。
- 仅在用户要求发布就绪判断时使用其验收范围；普通构建成功只报告构建与落盘状态。原因：构建、cook、可分发容器和运行结果分别需要对应证据。
- 具体打包字段和 Zenserver / Pak / IoStore 行为以当前工程配置与引擎为准，删除跨版本默认能力及 beta 状态保证。原因：项目的实际打包路径不会由历史文档里的版本标签决定。

按问题定位 `UGameUserSettings`、`UProjectPackagingSettings`、Asset Registry 和已有 trace/stat 输出；不因这些工具列在本页就运行全部采样。原因：每种工具回答的成本或依赖问题不同，所选证据应能支撑当前结论。

## 性能面板与离线导出归因

分析性能面板 JSON、修正 LOD/线程时间口径或定位 UI 长帧时，读取 [性能面板归因](references/performance-panel-attribution.md)。

## 怪群 GPU 与区域提前准备

同量蒙皮计算突然变慢、玩家装备随怪群变慢或 F6 驻留采集，读 [共享输出缓冲归因](references/shared-skinning-buffer-diagnosis.md)。提前分摊区域刷怪初始化、控制准备池内存和主客机生命周期，读 [区域提前准备](references/area-spawn-preparation.md)。

- 骨骼装备多个 LOD 仍保持全精度时，读取[连续长靴与渲染 LOD](../asset-model-workflow/references/continuous-boots-and-render-lods.md)：检查独立策略、最终渲染数据和重导入口，不能从减面比例推算帧率。 原因：几何数量只是部分成本，未经同场景采样不能换算成帧时间收益。

城市街区的实例、碰撞代理、连续道路及距离剔除优化，读取 [几何成本与城市实例口径](references/scene-geometry-cost-and-lod.md) 和 [城市分区制作](../ue5-pcg-building/references/city-district-production.md)。
