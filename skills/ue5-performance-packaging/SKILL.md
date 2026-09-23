---
name: ue5-performance-packaging
description: UE5.6-UE5.8 performance and packaging readiness workflow. Use when requests involve PIE performance checks, runtime stat review, pre-package validation, build configuration sanity, and release readiness checklists.
---

## UE5 默认开发方式（用户确定，2026-09-20）

**用户规则（2026-09-20）：禁止主动向其他对话/任务发送协调消息。** 不调用 send_message_to_thread 或跨任务消息工具询问占用、请求让位、通知释放、协商编译/重启；不通过轮询其他对话或共享留言板变相协调。接入等待交由桥的批次互斥处理，期间继续独立制作。真实文件/资产归属冲突或无法安全执行的编译/重启，保留现场，仅在当前对话向用户简要说明阻塞；不联系其他对话。此规则覆盖旧文中的“定向协调/集中协调”等要求；只有用户明确另行要求发送指定消息时才执行。

- **默认并行制作、短时接入（2026-09-20）。** 源码、外部模型/贴图/动画、生成与导入脚本先按文件和目标资产分工独立完成；只在需要实时 UE 状态或最终修改/导入/保存时进入 MCP。规则几何按需使用 Vibe3D，不要求所有制作全程占用编辑器。编辑器可保持打开，必要构建/重启按改动选择。
- 现有 C++ 函数逻辑按需使用 Live Coding；资产结构、新类落盘、模块/DLL 更换按具体条件安排常规构建和重启。停止 PIE 与关闭编辑器分别处理。
- 涉及编辑器操作或原生构建时，先读 [保持编辑器打开的开发规则](../ue5-auto-assistant/references/editor-open-development.md)，按表选择方式；多个会话按目标分工；接入统一走 mcp_call_codex.ps1，单次调用/整个 BatchFile 自动互斥。等待期间继续独立制作，不逐步询问其他对话；同一文件/资产归属冲突或编译/重启受阻时仅在当前对话报告用户，不向其他对话发送消息。
- **默认不主动检查、测试、启动 PIE、截图或验收渲染。** 必要制作、构建和接入照常完成，未测试交由用户测试；本规则优先于下文及引用中的旧默认验收步骤。

# Quick Start
- Confirm target platform and build configuration.
- Collect current performance symptoms and packaging goal.
- Output a pre-package checklist plus measurement plan.

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
- Every performance/packaging task must define:
  - target platform + build config + test map
  - reproducible capture scenario (camera path, duration, net mode)
  - baseline metrics and acceptance thresholds
  - packaging configuration set and dependency scan scope
  - go/no-go output with explicit blockers
- If any item is missing, readiness evaluation is incomplete.

# Workflow
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
- Do not claim optimization wins without measurable before/after data.
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
- Keep one source of truth for release packaging settings per target profile.
- In UE5.8, treat Zenserver cooked output as an iteration store; keep Pak/IoStore staging validation for distributable builds.
- Treat UE5.8 Incremental Cooking as a beta iteration path and retain a clean/full-cook release check.
- Re-run readiness checks after any packaging setting change.

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
- 细节与依据见 [UE MCP 多会话规则](../ue5-auto-assistant/references/mcp-multi-session.md)。

性能退化、内存与显存警告归因见 [性能退化诊断](references/performance-regression.md)。

## 性能面板与离线导出归因

分析性能面板 JSON、修正 LOD/线程时间口径或定位 UI 长帧时，读取 [性能面板归因](references/performance-panel-attribution.md)。
