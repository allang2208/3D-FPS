---
name: ue5-performance-packaging
description: UE5.6-UE5.8 performance budgeting, regression diagnosis, and packaging readiness. Use for FPSGAME hot-path, HUD, asset or streaming performance constraints, frame-time analysis, PIE performance work, and packaging readiness.
---

## UE5 默认开发方式（用户确定，2026-09-23）

后台优先：不主动启动 UE 编辑器；不主动检查、测试、启动 PIE、截图或验收渲染；不向其他对话/任务发协调消息。完整规则与「按改动选执行方式」表见仓库根 `AGENTS.md` 和 [后台开发与编辑器使用条件](../ue5-auto-assistant/references/editor-open-development.md)。

## FPSGAME 性能开发约束（2026-09-23）

功能开发涉及高频刷新、属性查询、场景生成、资源加载或图标时，先按改动范围读取 [FPSGAME 性能开发约束](references/fpsgame-performance-development.md)。把更新触发、重复工作和资源预算纳入实现，不等出现掉帧后再补；此入口不自动启动采样、测试或打包检查。

# Quick Start

- 启动前完整预加载、两档加载与纹理池准备，读取 [进入场景前的资源准备](references/entry-resource-preparation.md)，区分结构就绪、材质/纹理就绪和有限显存预算。
- Distinguish feature development, requested performance diagnosis, and packaging readiness.
- For development, apply the relevant FPSGAME performance constraints to the changed path.
- For requested measurements or packaging work, establish the target, scenario and available evidence; report missing evidence instead of inventing results.

# API Anchors (UE5.6-UE5.8)
- Runtime quality and frame-budget anchors:
  - `UGameUserSettings::SetOverallScalabilityLevel(...)`
  - `UGameUserSettings::SetFrameRateLimit(...)`
  - `UGameUserSettings::ApplySettings(...)`
- Packaging settings anchors:
  - `UProjectPackagingSettings`
  - `BuildConfiguration`, `MapsToCook`, `DirectoriesToAlwaysCook`
  - `UsePakFile`, `bUseIoStore`, `bGenerateChunks`
- Asset dependency validation anchors:
  - `FAssetRegistryModule`, `IAssetRegistry`
  - `GetAssetsByPath(...)`
  - `GetDependencies(...)`, `GetReferencers(...)`
- Profiling instrumentation anchors:
  - `TRACE_CPUPROFILER_EVENT_SCOPE(...)`
  - `DECLARE_CYCLE_STAT(...)`
- Practical runtime stat commands:
  - `stat unit`, `stat gpu`, `stat scenerendering`, `memreport -full`

# Performance and Packaging Contract
- For explicitly requested performance measurement or packaging readiness, define the applicable items:
  - target platform + build config + test map
  - reproducible capture scenario (camera path, duration, net mode)
  - baseline metrics and acceptance thresholds
  - packaging configuration set and dependency scan scope
  - go/no-go output with explicit blockers
- Missing required evidence limits the conclusion. Ordinary development does not trigger these measurements or packaging checks.

# Workflow
The capture, audit and readiness actions below apply only when requested; feature development follows the implementation constraints above.
## 1) Reproducible Baseline Capture
- Freeze test map, camera path, scalability, and net mode.
- Capture `stat unit` and `stat gpu` under same scenario repeatedly.
- Use median or percentile metrics, not single-frame spikes.
- **Read the thread numbers with the right semantics before drawing conclusions**；
  本机引擎源码核对过的口径与陷阱见
  [帧预算统计的正确读法](references/frame-budget-stat-semantics.md)。
  三条最容易踩的：`...Time` 不含空闲而 `...TimeCriticalPath` 含依赖等待（关键路径长
  **不等于** GPU 受限）；`GGameThreadTime` 是帧间隔减空闲（不可能超过帧时间）；
  Game 与 Draw 在时间上重叠，**不得相加**。

## 2) Hotspot Isolation
- Identify top-cost gameplay/render systems in the capture window.
- Correlate high-cost actors/assets with scene context.
- Add scoped CPU markers for custom systems when attribution is unclear.
- 逐组件 tick 耗时与逐图元 GPU 耗时**都拿不到**（`FTickTaskLevel` 私有、MSM 不导出），
  不要做「某组件花了 X 毫秒」的界面。可替代做法是统计**昂贵 setter 的每帧调用速率**：
  见 [帧预算统计的正确读法](references/frame-budget-stat-semantics.md) 第 6 节。

## 3) Asset and Dependency Validation
- Scan target paths for missing or broken asset references.
- Query dependencies and referencers for problematic assets.
- Validate required map/game mode assets are included in package scope.

## 4) Packaging Configuration Validation
- Check `UProjectPackagingSettings` fields for target release policy.
- Validate maps-to-cook, always-cook directories, and build configuration.
- Validate Pak/IoStore/chunk strategy against distribution requirements.

## 5) Package Readiness Trial
- Run pre-package checklist and dry-run style verification.
- Isolate first blocking packaging error and dependency chain.
- Record unresolved blockers with owner and risk.

## 6) Go/No-Go Decision
- Approve only when metrics and packaging checks meet thresholds.
- Report remaining risks and recommended mitigation actions.
- Lock scenario and settings used for sign-off evidence.

# Constraints
- Separate user-reported improvement from measured gains; quantify improvements only with comparable before/after data.
- Keep profiling scenario reproducible (map, camera path, net mode).
- Distinguish editor overhead from packaged runtime behavior.
- Avoid changing quality scalability settings without reporting it.
- Keep packaging checks deterministic; avoid ad-hoc config toggles during sign-off.
- Always report metric units (ms, fps, memory) and capture duration.

# Failure Handling
- Symptom: one localized feature stalls an entire open-world map (e.g. adding a small voxel volume makes every terrain cell slow).
  - Locate: the feature brought a **second terrain/streaming pipeline** (its own chunk meshing, collision cooking, thread pool) that competes with the existing one, usually with demo-oriented defaults such as "cook collision for every visible chunk" or an uncapped LOD.
  - Fix: treat "two terrain backends side by side" as the worst case - ask first whether the existing backend can express the feature, then A/B it off (`stat unit` -> `stat game` -> the subsystem's own stat) instead of guessing; if the second pipeline stays, cap its LOD, replace per-visible-chunk collisions with invoker-radius collisions, shrink its bounds, and re-measure before shipping.
- Symptom: performance data is noisy across runs.
  - Locate: non-deterministic scenario setup and background variance.
  - Fix: lock scenario, warm up run, and compare median/percentile values.
- Symptom: optimization claims do not reproduce.
  - Locate: mismatched quality settings, map, or runtime mode.
  - Fix: publish exact capture config and rerun before/after under same conditions.
- Symptom: package build fails with long error cascade.
  - Locate: first blocking error and its direct dependency chain.
  - Fix: resolve earliest blocker first; rerun to reveal next blockers.
- Symptom: cook dies with an engine assertion instead of a content error, e.g.
  `Assertion failed: !Hash.IsZero() ... AnimSequence.cpp`.
  - Locate: it is a **missing asset dependency**, not a cooker bug. Search the same log for
    `has a dependency on package ... which does not exist` to get the exact package list, and for
    `Skeleton == nullptr` / `Zero key hash compressed animation data` to confirm the anim family.
    In the 2026-09-23 case six packages referenced a Skeleton that had never been saved to disk
    since the original import; the editor never complained, so it surfaced only at the first cook.
  - Fix: restore the missing asset at the path the clips already reference (the name match restores
    the binding automatically), read the reference back in a new process, then re-cook. Do not
    "solve" it by dropping the AlwaysCook entry — that silently ships a package without those clips.
- Symptom: packaged build launches with missing assets.
  - Locate: cook list coverage and dependency graph gaps.
  - Fix: include missing maps/directories and resolve broken references.
- Symptom: packaged build perf is worse than PIE baseline.
  - Locate: packaged-only config differences and runtime content path.
  - Fix: compare packaged config to baseline and align scalability/device settings.
- Symptom: memory usage regresses near content-heavy scenes.
  - Locate: high-memory assets and streaming policy behavior.
  - Fix: reduce resident asset pressure and adjust streaming/cook strategy.

# Packaging Ops
- Prefer explicit map/cook lists over implicit discovery for release builds.
- Use AssetRegistry queries to validate dependencies before packaging.
- **Run a dependency pre-flight before the first real cook of a project**
  （本机 2026-09-23 首次 Cook 就撞上：`AnimSequence` 引用的 Skeleton 包缺失时，
  Cooker 不用清晰报错，而是在 `AnimSequence.cpp` 断言 `!Hash.IsZero()` 直接崩掉整次 Cook）。
  预检要点：凡按槽位/骨架导入的骨骼资产，在新进程里读回 `SkeletalMesh.get_editor_property('skeleton')`
  非空；再用 `LogCook` 的 `has a dependency on package ... which does not exist` 反查缺口清单。
  这类缺陷在编辑器里不报错（缺骨架的组件不会立刻失败），只在 Cook 暴露。
- Keep one source of truth for release packaging settings per target profile.
- In UE5.8, treat Zenserver cooked output as an iteration store; keep Pak/IoStore staging validation for distributable builds.
- Treat UE5.8 Incremental Cooking as a beta iteration path and retain a clean/full-cook release check.
- Re-run readiness checks after any packaging setting change.
- 打包运行器不要把 `RunUAT` 当普通可执行文件：它是批处理，`Start-Process -PassThru` 在本机
  对失败的构建返回**空退出码**（曾把一次失败报成成功）。用调用运算符 + `$LASTEXITCODE` 取真实退出码。
  另外要区分**编译失败**与 **Cook 失败**：前者可能是并行会话的在途改动，重试有意义；后者重试无意义。

# UE5.6-UE5.8 Compatibility Notes
- `UGameUserSettings`, `UProjectPackagingSettings`, and AssetRegistry APIs above are stable in UE5.6-UE5.8.
- `ProjectPackagingSettings.h` lives under `Developer/DeveloperToolSettings` across UE5.6-UE5.8.
- UE5.8 enables Zenserver as the cooked output store by default for supported iteration workflows; this does not replace release container validation.

# Escalation
- Escalate when performance bottleneck requires engine-level profiling or renderer changes.
- Escalate when packaging issues stem from third-party plugin build failures.

## UE MCP 多会话并发规则（用户指定 2026-09-18）

**多个会话可以同时通过 MCP 在 UE 里工作和修改**——UE 5.8 内置 MCP 服务支持多会话，不得因为"可能有别的会话在用编辑器"就拒绝或跳过 MCP 工作。

- 端点：`http://127.0.0.1:<ServerPortNumber><ServerUrlPath>`（本项目 8000/`/mcp`，配置在 `D:/FPS3D/FPSGAME/Config/DefaultEditorPerProjectUserSettings.ini`）；桥脚本 `Tools/AssetPipeline/mcp_call_codex.ps1`。
- **一个时刻只有一个写入者**：所有会话跑在同一个编辑器主线程、共享同一份资产/关卡，没有事务与锁。制作开始时按文件/资产划分归属，实际冲突仅向当前用户报告；接入通过桥的批次锁排队，不逐条询问其他会话，不覆盖他人未提交改动。
- 编辑器内只读调用也经同一桥排队，避免插入其他任务的接入批次；编辑器外文件读取可并行。
- 桥脚本 session 缓存在 `%TEMP%\codex-ue-mcp-session.json`，同机多会话共用：要独立会话加 `-NewSession`。
- 会硬碰硬的三处：C++ 编译（Live Coding/UBT 只有一个编译窗口）、PIE（一个编辑器同时只有一个 PIE 会话）、同一资产的导入/保存；撞上就排队，别杀进程、别抢别人的编辑器或端口。
- 细节与依据见 [后台开发与批次互斥规则](../ue5-auto-assistant/references/editor-open-development.md)。

性能退化、内存与显存警告归因见 [性能退化诊断](references/performance-regression.md)。

## 性能面板与离线导出归因

分析性能面板 JSON、修正 LOD/线程时间口径或定位 UI 长帧时，读取 [性能面板归因](references/performance-panel-attribution.md)。

## 场景几何成本与 LOD 收敛（2026-09-23）

给网格补 LOD 链、对大面积平铺件强制 LOD、判断"该不该合并/实例化重复构件"、
或需要确认 `all_rank_total` 与 `gpu0`/`draw` 各自能证明什么时，读取
[场景几何成本与 LOD 收敛](references/scene-geometry-cost-and-lod.md)。
要点：`all_rank_total` 是 LOD0 口径、**看不出 LOD 效果**；组件数是否为主要开销要先分别测
`draw` 与 `gpu0` 再下结论；UE 5.8 生成 LOD 走 `StaticMeshEditorSubsystem.set_lods`
（不是 `EditorStaticMeshLibrary.set_lod_count`）。
