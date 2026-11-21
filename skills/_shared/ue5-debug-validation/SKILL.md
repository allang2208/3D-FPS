---
name: ue5-debug-validation
description: UE5.6-UE5.8 debugging and validation workflow for logs, asset checks, and regression triage. Use when requests involve troubleshooting why gameplay does not work, validating expected output, narrowing minimal repro, and producing concrete fix steps.
---

# 按用户指定范围排障

**第一条（FPSGAME）　文件位置与引用路径。** 以含 `FPSGAME.uproject` 的当前工程根为准，先读 `Docs/Production/README.md` 和 `WORKFLOW.md` 第 4.1 节。先确定制作源、正式资产和输出目录，再创建或引入文件。工程 Content 资产用 `/Game/...` 包名引用，制作脚本从工程根或已配置的制作源根解析相对路径。交付时在同一功能条目登记实际位置、引用及备份状态。

- 本技能只在用户要求排障、检查或验证时启用；测试、截图、渲染和回归各自以用户要求的范围为限。原因：修复授权不自动包含运行测试，更不包含扩展到相邻系统的回归。
- 优先读取已有错误、复现描述和相关源码，记录预期、实际偏差及当前环境；资料不足时明确缺口。原因：不完整的现场仍可推进定位，不应为了补齐固定清单强制启动游戏。
- 按失败时间和对象缩小日志范围，沿调用链找最早出现的偏差。原因：下游报错通常只是同一上游故障的结果，全量日志会掩盖首次失败。
- 每个推断标明证据与尚未排除的条件；用户要求实验时，一次只改变能区分假设的条件。原因：多个变量同时改变后无法判断哪一项解释了故障。
- 只修改已定位的原因，保留原始失败信息；需要临时日志时限定对象和生命周期。原因：大范围重构或永久调试输出会混入与故障无关的行为及开销。
- 涉及共享编辑器、Live Coding、结构布局或已加载资产时，按[后台开发规则](../ue5-auto-assistant/references/editor-open-development.md)处理。原因：热补丁、基础 DLL 和保存资产的状态不同，不能统一靠关闭编辑器或重新制作资产解决。
- 交付分别说明定位依据、实际修改、必要构建和已执行的用户指定验证；未测试交由用户测试。原因：编译成功不能证明运行路径或视觉结果正确。

## 工具与诊断入口

这些是按故障选择的线索，不是每次都要执行的清单。原因：诊断手段只有能区分当前假设时才提供有效证据。

| 线索 | 使用位置 | 保留原因 |
| --- | --- | --- |
| `UE_LOG`、`FMessageLog` | 已有输出与有限的故障标记 | 类别、时间和对象能关联同一条失败链。 |
| `ensure` / `check` | 阅读现有断言及其前置条件 | 断言说明代码假定，不能为了排障随意新增可能终止进程的检查。 |
| Asset Registry | 用户要求的缺失资产、依赖和引用定位 | 磁盘文件存在不代表运行引用能够解析。 |
| 运行或平台工具 | 用户明确要求且当前问题需要时 | 不同运行配置和 cook 结果可能改变加载路径。 |

## 按故障读取资料

| 故障范围 | 资料 | 保留原因 |
| --- | --- | --- |
| 地表模糊、材质就绪、近处优先加载 | [动态地表材质加载](references/dynamic-terrain-material-loading.md) | 区分纹理驻留与生成/加载排队。 原因：地表的实际渲染与数据编码决定材质输入，不能把另一种地形后端的节点直接套入。 |
| 云不可见、雷电与声音仅有日志 | [云与音画诊断](../ue5-weather-workflow/references/cloud-lightning-audio.md) | 触发、材质输入、混音和用户感知不是同一层证据。 |
| 用户要求天气过渡检查 | [天气过渡](../ue5-weather-workflow/references/storm-rain-integration.md) | 采样时机必须覆盖实际光照写入方。 原因：环境的可见表现与实际状态更新需要同一时间依据，否则过渡和玩法消耗会偏离。 |
| 导入场景、出生悬空、重定位 | [场景与出生点](references/scene-import-spawn-validation.md) | 坐标、碰撞和出生流程需要分开定位。 |
| 热补丁后才出现的问题、资产字段为空 | [热编译与常规构建](references/live-coding-vs-full-build.md) | 进程状态、结构布局和磁盘二进制可能不一致。 |
| 攀爬接触、相机交接、表面 IK | [攀爬接触](../ue5-fps-arms-animation/references/traversal-contact.md) | 接触几何和相机占用决定问题所属路径。 |
| 用户要求材质中间量排查 | [Emissive 探针](references/material-emissive-probes.md) | 隔离材质输入有助于区分遮罩与光照问题。 |
| 默认材质回落与用户指定无界面渲染 | [材质回落](references/material-fallback-and-commandlet-render.md) | 编译、加载与渲染上下文分别影响结果。 |
| 预览世界释放、EndPIE、DynamicWind | [预览生命周期](references/preview-scene-lifecycle.md) | 世界释放与渲染线程资源释放可能不同步。 |
| 用户要求多进程运行 | [运行负载与证据](references/multi-process-runtime-evidence.md) | 独立宿主仍竞争同一硬件，不能混同源码和运行证据。 |
| 地图存在但载入失败、无界面预热停滞 | [地图预加载](references/map-preload-and-headless-dungeon.md) | 包存在与加载门禁满足是不同条件。 |
| 用户要求权威命中夹具 | [权威命中夹具](references/authority-hit-fixture.md) | 夹具覆盖范围不等于真实 RPC 分派覆盖范围。 |
| 无界面动画加载触发事务崩溃 | [骨架曲线迁移](references/uncooked-animation-curve-migration.md) | 骨架元数据引用可能是实际故障源，仅重存动画无法修复。 |
| 用户要求丘陵联机生命周期检查 | [丘陵生命周期](references/hills-network-lifecycle.md) | 拾取、重连和换图依赖不同的生命周期入口。 |
| 静止时树草周期性闪灭 | [PCG 属性通知](references/pcg-property-change-flicker.md) | 组件被重建与仍存在但漏绘需要不同修复。 |
| 用户要求地图联机检查及宿主归档 | [地图联机证据](references/map-marker-network-evidence.md) | 无渲染证据不能代替真实界面结果。 |
| 用户要求丘陵截图或材质回执 | [截图宿主与材质回执](references/hills-capture-and-material-receipts.md) | 包保存回执和截图所用世界必须明确对应。 原因：作者脚本描述制作过程，只有执行并保存的产物才可供引擎实际引用。 |
