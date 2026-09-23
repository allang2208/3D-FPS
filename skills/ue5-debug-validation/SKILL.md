---
name: ue5-debug-validation
description: UE5.6-UE5.8 debugging and validation workflow for logs, asset checks, and regression triage. Use when requests involve troubleshooting why gameplay does not work, validating expected output, narrowing minimal repro, and producing concrete fix steps.
---

## UE5 默认开发方式（用户确定，2026-09-23）

后台优先：不主动启动 UE 编辑器；不主动检查、测试、启动 PIE、截图或验收渲染；不向其他对话/任务发协调消息。完整规则与「按改动选执行方式」表见仓库根 `AGENTS.md` 和 [后台开发与编辑器使用条件](../ue5-auto-assistant/references/editor-open-development.md)。

# Quick Start
- For blurry DynamicMesh ground, material-readiness stalls or nearby-first world loading, read [dynamic terrain material loading](references/dynamic-terrain-material-loading.md).
- For invisible cloud fields or logged lightning/thunder without perceptible output, read [cloud and A/V diagnosis](../ue5-weather-workflow/references/cloud-lightning-audio.md); distinguish material inputs, trigger state, mixer capture and user feedback.
- For weather/cloud validation, read [weather transition diagnostics](../ue5-weather-workflow/references/storm-rain-integration.md); sample after all light writers and distinguish editor actor enumeration from runtime world state.
- For imported maps, spawn/floating bugs and relocation, read [scene validation](references/scene-import-spawn-validation.md).
- For changes that only reproduce in one editor session, whether a hot patch can carry a change, or assets reading back as None, read [live coding vs full build](references/live-coding-vs-full-build.md).
- Reproduce issue with minimal steps.
- Collect output log lines and relevant actor/asset state.
- Classify fault domain: data, Blueprint, C++, networking, or editor config.

# API Anchors (UE5.6-UE5.8)
- Core diagnostics anchors:
  - `UE_LOG(...)`
  - `ensure(...)`, `ensureMsgf(...)`
  - `check(...)`, `checkf(...)`
- Runtime debug output anchors:
  - `UEngine::AddOnScreenDebugMessage(...)`
  - `UKismetSystemLibrary::PrintString(...)`
- Structured log review anchors:
  - `FMessageLog::Info(...)`
  - `FMessageLog::Warning(...)`
  - `FMessageLog::Error(...)`
- Asset/config verification anchors:
  - `FAssetRegistryModule`, `IAssetRegistry`
  - `GetAssetsByPath(...)`
  - `GetDependencies(...)`, `GetReferencers(...)`

# Debug Stage Contract
- Every debug task must define:
  - reproducible scenario and expected vs observed behavior
  - data capture set (logs, runtime state, asset/config snapshot)
  - first bad transition candidate in the execution pipeline
  - hypothesis list ranked by probability and verification cost
  - fix validation and regression scope
- If any item is missing, diagnosis output is incomplete.

# Workflow
## 1) Reproduce and Freeze Context
- Build a minimal deterministic repro with exact steps and preconditions.
- Capture map, actor setup, input sequence, and runtime mode.
- Define expected result and observed deviation.

## 2) Capture Signals
- Filter logs by relevant categories and timestamps around failure window.
- Add targeted debug markers (`UE_LOG`, on-screen debug, or Blueprint print) if needed.
- Capture relevant state snapshots at stage boundaries.

## 3) Validate Data and Assets
- Verify key assets/classes/config entries exist and resolve correctly.
- Check dependencies/referencers for missing or mismatched assets.
- Confirm runtime-loaded data matches expected environment.

## 4) Locate First Bad Transition
- Walk pipeline step-by-step and identify earliest divergence point.
- Separate root cause from downstream noise symptoms.
- Prioritize smallest fixable cause with highest confidence.

## 5) Hypothesis and Verification
- Rank hypotheses by probability and verification cost.
- Run one focused test per hypothesis to avoid cross-contamination.
- Keep rejected hypotheses documented with evidence.

## 6) Fix and Regression Validation
- Apply minimal fix and rerun the same repro scenario.
- Validate no regression on adjacent systems/paths.
- Output fix summary with confidence and residual risk.

# Constraints
- Avoid broad refactors during diagnosis.
- Keep repro deterministic and documented.
- Prefer observable checks over assumptions.
- Separate root cause from secondary noise.
- Do not mix instrumentation changes with functional fixes in one step.
- Preserve failing evidence before introducing mitigation changes.

# 无头进程的物理查询不可信（2026-09-17）

1. **`-run=pythonscript` commandlet 里，物理查询只认本进程新建的 actor**：从 `.umap` 读入的关卡几何（连地面都算）永远不返回命中，"射线没打中 = 这里通的"是**假阴性**，不能作为通行性/碰撞结论。判据：先打一条**正对照**（对刚 spawn 的 actor 或已知实心处），命中才说明这一次查询可信。
2. **碰撞判定要在运行中的编辑器里做**（`Tools/AssetPipeline/ue_python_exec.py`），那里的物理是活的。该通道里 `HitResult` 的 `location`/`hit_actor` 读不出来，改用 `SystemLibrary.sphere_overlap_actors(WorldContext, Pos, Radius, ObjectTypes, ActorClassFilter, ActorsToIgnore)` **点名阻挡者**——2026-09-17 凉亭"进不去"就是这样一步定位的（穹顶的生成碰撞罩住了整个内部）。
3. **射线扫掠要覆盖角色胶囊的全身高度**：42 半径球在 z=30 会碰到地面造成假命中、在 z=150 又漏掉脚下；至少取 60/96/150 三个高度，并先确认扫掠高度不会自顾自压到地面。

# 资产"看不见/没图/发黑"的网格法证（2026-09-17）

面板缩略图缺失、模型发黑、某件"没显示"这类症状，先怀疑网格本身，用现成招式给数字（离线，无需渲染）：

1. 导出三角面汤（Vibe3D `load_mesh_from_static_mesh` → `get_dynamic_mesh` → 逐面 `get_triangle_positions`/`get_triangle_face_normal`），比对**存储法线 vs 环绕方向**（UE 引擎约定顺时针为正面，离线右手定则比对会整体反号）与**退化面**数量。
2. 再算**背离整体的面占比**：健康闭合件应接近 100%；出现大面积内向面就是法线被并集/布尔破坏。
3. 与一个**已知正常**的同类件逐项对照（面数、连通体、闭合、开放边、不一致率）——三项以上完全相同即可排除网格，去查渲染/缓存/引用链路。

案例：`SourceAssets/RomanColumn20260915/forensic_rails_20260917.py`（三根顶梁指标完全相同 → 排除网格，定位到图标缓存上限与永久拉黑）；凉亭"没图"最终用同参数复现渲染（`probe_icon_capture_20260917.py`）证伪了"渲染失败"假设。

# Failure Handling
- Symptom: cannot reproduce issue consistently.
  - Locate: missing preconditions, race windows, or nondeterministic setup.
  - Fix: tighten repro setup and add targeted instrumentation checkpoints.
- Symptom: logs contain too much unrelated noise.
  - Locate: broad log categories and missing temporal scoping.
  - Fix: narrow category filters and focus around failure timestamps.
- Symptom: multiple plausible causes remain.
  - Locate: shared downstream symptom without first-failure isolation.
  - Fix: split into independent hypotheses and run low-cost discriminating tests.
- Symptom: issue disappears after adding debug output.
  - Locate: timing-sensitive/race-sensitive behavior.
  - Fix: use low-overhead markers and repeat with controlled timing.
- Symptom: fix resolves one path but breaks another.
  - Locate: hidden coupling between systems or config layers.
  - Fix: keep fix minimal and extend regression matrix around impacted paths.
- Symptom: runtime mismatch only happens on packaged builds.
  - Locate: build config/cook differences versus editor run.
  - Fix: compare packaged and editor config/assets and validate load order.
- Symptom: a bug only reproduces in the session where the code was hot patched.
  - Locate: file-scope static state reset by the module reload, or an in-session patch that never reached the on-disk binary.
  - Fix: move the state into a UPROPERTY member or re-resolve it from a safe host, then confirm with a full build instead of trusting the patch.
- Symptom: asset fields read back as None right after a code change.
  - Locate: a USTRUCT that backs an asset had its layout or defaults changed through a hot patch, so the saved tag no longer matches.
  - Fix: close the editor, full build, then re-author the asset; verify with disk timestamp, byte scan and an independent process read-back.

# Validation Ops
- Always keep a minimal repro artifact (steps, map, config) with the diagnosis.
- Always include first-failure evidence, not only final symptom logs.
- Always provide a verification checklist for the proposed fix.
- Always state residual risk when confidence is below high.

# UE5.6-UE5.8 Compatibility Notes
- Logging/assertion/message/asset-registry APIs listed above are stable across UE5.6-UE5.8.
- Prefer runtime-safe diagnostics for validation paths that must run outside editor.

# Escalation
- Escalate when failure is inside engine/plugin internals not owned by project code.
- Escalate when diagnosis needs platform-specific profiling tools unavailable in current environment.

FPSGAME traversal geometry, camera handoff and surface IK: [traversal contact](../ue5-fps-arms-animation/references/traversal-contact.md).

## 假故障：成员指针读到 0／CDO 构造崩溃（构建缓存陷阱，2026-09-18）

给一个 `UCLASS` 加子类、并把基类成员从 `private` 挪到 `protected`（**类布局变了**）之后，子类 CDO 构造直接
`EXCEPTION_ACCESS_VIOLATION`。特征与判读：

- 崩溃栈落在**新加的子类构造函数**那一行（如 `Frame->SetStaticMesh(...)`）；在同一构造函数里打点会看到
  **一部分成员正常、一部分为 0**（`frame=0 leafL=1 leafR=1`）＝读到了错误偏移，**不是逻辑错误**。
- 根因：本工程构建脚本带 **`-NoUBTMakefiles`**（不重生成 makefile），改了头文件布局后依赖它的 .cpp 可能**没被重编**，
  obj 仍是旧布局。
- 排查顺序：先比对 `Intermediate/Build/Win64/x64/<Target>/Development/FPSGAME/<File>.cpp.obj` 的 mtime 与源码 mtime，
  让出问题的 .cpp 重编一次（或去掉 `-NoUBTMakefiles` 跑一遍）即可恢复；**不要先去改代码逻辑**，那只会越走越远。
  改头文件布局后主动重编相关模块再继续。
- 通用判据：同一进程里"部分成员正常、部分为 0／垃圾"，优先怀疑 obj 与头文件不同版；其次才是初始化顺序／内存问题。
- 另外：判断自己的改动有没有进二进制，用**字符串自证**比时间戳硬——例如 `python -c` 扫 DLL 里的 UTF-16 文本字面量
  （网格路径、提示串），比只对时间戳可靠；本仓库 `git diff` 展示可能错序，疑似编译错误必须核对真实文件。

### -game 实机审计夹具模式（2026-09-19 QuickCombatAudit 先例）

无头 commandlet 拿不到真实渲染/相机/动画链路，编辑器远程通道在 PIE 下截图是黑图——需要
**实机画面级取证**时，克隆步枪冲刺夹具的模式（`FPSGAMERifleSprintAudit.cpp` /
`FPSGAMEQuickCombatAudit.cpp`）：

- 入口：`RunGunplayAcceptance` 里按命令行旗标分发（`-GunplayAudit -<Task>Audit
  -ColdSteelProfile=<Task>Audit-<label> -GunplayLabel=<label>`）；`bAudit` 只看命令行
  是否含 "Audit"，Profile 槽位名再自查防串。
- 跑法：`UnrealEditor.exe <uproject> <小验证图> -game -windowed -RenderOffscreen
  -ResX=960 -ResY=540 -unattended -nosound -UseFixedTimeStep -FPS=60 -GunplayCaptureFrames`；
  **可与用户开着的编辑器并存**（独立进程只读）。本机首跑要等 ~30-40s 资产编译。
- 帧捕获：`FScreenshotRequest::RequestScreenshot(绝对路径, false, false)`，30Hz 门控
  `!IsScreenshotRequested()`；**退出前要留 ≥1s 让异步回读落盘**（否则 0 帧且不报错）；
  退出时用 `IFileManager::FindFiles` 把磁盘帧数写进 results.log 自证。
- 世界变换 CSV：相机/关键骨骼/打击端逐帧落盘（屏幕 u,v 用
  `PC->ProjectWorldLocationToScreen`，相机身后返回 false 要显式标记，否则投影翻转成
  假"出画"）。
- 产物在 `Saved/<Task>Audit/<label>/`；对照视频用 ffmpeg 拼帧（imageio_ffmpeg 自带
  ffmpeg：`-framerate 10 -i Frame_%04d.png` + `setpts` 慢放 + `eq` 提亮）。
