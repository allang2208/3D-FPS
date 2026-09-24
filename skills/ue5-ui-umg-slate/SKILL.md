---
name: ue5-ui-umg-slate
description: Plan and implement UE5.6-UE5.8 panels, tabs, sections, cards and popups using UMG and Slate. Use for new UI or UI upgrades, FPSGAME Cold Steel design rules, panel/column workflows, Widget Blueprint setup, lifecycle binding, data visibility, input/focus, tooltips and viewport layout.
---

## UE5 默认开发方式（用户确定，2026-09-23）

后台优先：不主动启动 UE 编辑器；不主动检查、测试、启动 PIE、截图或验收渲染；不向其他对话/任务发协调消息。完整规则与「按改动选执行方式」表见仓库根 `AGENTS.md` 和 [后台开发与编辑器使用条件](../ue5-auto-assistant/references/editor-open-development.md)。


## FPSGAME 性能开发约束（2026-09-23）

新增 HUD、快捷栏、状态面板或图标时，读取 [性能开发约束](../ue5-performance-packaging/references/fpsgame-performance-development.md) 的高频路径与图标部分。先明确刷新触发和调用链，复用属性读取与可见条目，不把重复 JSON 解析、全量控件重建或资源等待放进 NativeTick。

# Quick Start

- 启动选档、进场加载、重试与取消页面，读取 [资源准备与交互状态](../ue5-performance-packaging/references/entry-resource-preparation.md)，沿用 `TransitLoadingSubsystem` 和冷钢共享样式。
- For FPSGAME building categories, construction cards, model thumbnails, fonts or detail popups, read [the building-panel standard](references/building-panel.md).
- For FPSGAME persistent panel icons, hotkey effects, dual-pistol layout, or melee stamina readouts, read [HUD navigation and weapon readouts](references/hud-navigation-and-weapon-readouts.md).
- For FPSGAME new panels, tabs, sections, cards, or UI upgrades, first read [panel planning and Cold Steel rules](references/fpsgame-panels.md). Plan structure, layout, data scope and states before implementation; use the project's current design system.
- For FPSGAME inventory drawers, detached item menus, or drag/close regressions, read [inventory input and validation](references/fpsgame-inventory-input.md).
- For a blurry weapon/item preview, incomplete-looking materials, or transparent SceneCapture composition, read [preview rendering and texture residency](references/preview-rendering.md).
- Identify whether feature belongs to UMG, Slate, or hybrid bridge.
- Define data source component/subsystem and UI binding point.
- Output widget tree intent and runtime binding sequence.

# API Anchors (UE5.6-UE5.8)
- UMG lifecycle and viewport anchors:
  - `UUserWidget::NativeConstruct()`, `UUserWidget::NativeDestruct()`
  - `UUserWidget::AddToViewport(...)`
  - `UWidget::RemoveFromParent()`
  - `UWidget::SetVisibility(...)`
  - `UWidget::SetKeyboardFocus()`
- UMG input mode anchors:
  - `UWidgetBlueprintLibrary::SetInputMode_UIOnlyEx(...)`
  - `UWidgetBlueprintLibrary::SetInputMode_GameAndUIEx(...)`
  - `UWidgetBlueprintLibrary::SetInputMode_GameOnly(...)`
- UMG/Slate bridge anchors:
  - `UWidget::TakeWidget()` for Slate bridge hand-off
  - `SCompoundWidget`, `SLATE_BEGIN_ARGS(...)`
  - `FSlateApplication::SetKeyboardFocus(...)`, `SetUserFocus(...)`
- Viewport geometry anchor:
  - `UGameViewportClient::GetViewportSize(...)`

# UI Stage Contract
- Every UI task must define:
  - UI layer ownership (UMG-only, Slate-only, or hybrid bridge)
  - data source and update trigger (pull, push, event, or mixed)
  - focus and input ownership transition
  - viewport-safe placement behavior for tooltip/popup
  - teardown/cleanup path for unbinds and widget removal
- If any item is missing, the UI implementation is incomplete.

# Workflow
## 0) Panel / Section Plan
- Locate the nearest existing panel and current project design system before changing UI.
- Define information hierarchy, responsive layout, fixed/scrolling regions, shared visual roles, data scope, empty/disabled/selected states, and action/save ownership.
- Continue within the user's authorized phase. A planning step does not require an extra approval when implementation is already authorized.
- In FPSGAME, do not launch checks, tests, screenshots, or acceptance runs unless explicitly requested; necessary development and builds still proceed.

## 1) UI Architecture Decision
- Select UMG for standard game HUD/menu work.
- Select Slate for custom rendering/input behavior that UMG cannot express cleanly.
- Select hybrid when a `UWidget` host needs to embed custom Slate content.

## 2) Construct and Lifetime
- Initialize widget bindings in construct/init path.
- Register event listeners once and store handles when required.
- Define destruct/unregister logic explicitly to avoid stale bindings.

## 3) Data Binding and Refresh
- Bind runtime data from one authoritative source (subsystem/component/view model).
- Use event-driven refresh for high-frequency data where possible.
- Keep display widgets read-only for gameplay state mutation.

## 4) Input and Focus Ownership
- Set input mode deliberately when opening/closing UI contexts.
- Set keyboard/user focus to intended root widget.
- Ensure focus return path back to gameplay on close.

## 5) Tooltip/Popup Viewport Clamp
- Compute desired tooltip position from anchor and cursor/widget geometry.
- Clamp final placement to viewport bounds to avoid off-screen rendering.
- Debounce high-frequency hover updates to avoid flicker.

## 6) Remove and Cleanup
- Remove widget from parent or viewport on close.
- Clear timers/delegates and transient references.
- Confirm no duplicate instances persist after reopen.

# Constraints
- Keep UI rendering and gameplay state mutation separated.
- Avoid direct gameplay writes from passive display widgets.
- Clamp tooltip and popup placement to viewport bounds.
- Prefer deterministic input ownership and focus transitions.
- Keep Slate-only code isolated behind clear bridge boundaries.
- Do not rely on per-frame polling if event-driven updates are available.

# Failure Handling
- Symptom: widget appears but never refreshes.
  - Locate: construct timing, binding registration, source event firing.
  - Fix: bind after source readiness and verify event subscription path.
- Symptom: widget refreshes once then stops.
  - Locate: lost delegate handle or widget recreated without rebind.
  - Fix: rebind on construct and unbind on destruct; prevent duplicate create/destroy churn.
- Symptom: input is swallowed by UI unexpectedly.
  - Locate: current input mode and focused widget path.
  - Fix: enforce intended input mode and set explicit focus target.
- Symptom: keyboard/controller navigation breaks after popup open.
  - Locate: focus transfer and return path.
  - Fix: store previous focus owner and restore on popup close.
- Symptom: tooltip flickers near screen edges.
  - Locate: oscillating clamp output and hover source jitter.
  - Fix: debounce hover updates and clamp with stable viewport metrics.
- Symptom: memory growth after repeated open/close.
  - Locate: stale delegate/timer/reference retention.
  - Fix: clear bindings and transient refs in teardown.

# UE5.6-UE5.8 Compatibility Notes
- UMG lifecycle, input mode, and Slate focus APIs listed above are stable in UE5.6-UE5.8.
- Prefer Enhanced Input + explicit UI input mode ownership across all supported versions.

# Escalation
- Escalate when behavior requires engine-level Slate customization beyond project scope.
- Escalate when UI architecture conflicts with existing CommonUI framework decisions.

# FPSGAME Reference
- For this project's Buff / Debuff display, read [the status-effects bridge](references/fpsgame-status-effects.md).

## 技能图标系列

生成或替换冷钢技能图标时，读取 [技能图标系列](references/skill-icon-series.md)。

## 弹药袋与圆形选择

弹药袋子页、按弹种数量等分的 R 轮盘、鼠标选择和图标缓存，读取 [动态弹种轮盘与弹药袋](references/ammo-radial-and-pouch.md)。

## C++ 动态构建面板的硬教训（2026-09-24 冶炼面板，实测踩坑）

- **非 UWidget 的点击代理对象要专列数组保命**：给 `FScriptDelegate`/`AddDynamic` 绑定的
  `NewObject` 辅助 UObject 若塞进"每次刷新都 `Reset()`"的行对象缓存数组，GC 会在两次刷新之间
  回收代理，事件**静默失效**（不报错、不崩溃）。此类对象放专用 `UPROPERTY` 数组，永不随列表重建清空；
  回归测试必须"先 `CollectGarbage()` 再 `OnClicked.Broadcast()`"才有效。
- **贴缝凸舌（tab）不是卡片**：想让按钮"长在"面板上，就把描边/圆角卡片底全部拿掉——本体填充色
  **跟随所贴主体**（收起用面板色、展开用弹层色，ZOrder 盖住接缝），内层按钮 Normal 透明、只在
  Hover/Pressed 浮轻底；需要逐角半径（贴缝侧直角）时用 `ColdSteelUI::RoundedBrushCorners`
  （FSlateRoundedBoxBrush 的 FVector4 半径版），并让凸舌压过接缝 1~2px 消抗锯齿发丝。
- **UTextBlock 多行默认左对齐**：竖排"升\n级"要 `SetJustification(ETextJustify::Center)` 才逐行居中，
  CJK 双行贴紧可配 `SetLineHeightPercentage(0.88)`。
- **交付措辞看二进制状态**：编辑器开着时改的 C++ 一律"未生效"；看守构建要先在日志里确认
  `Result: Succeeded` 再告诉用户重开（用户往往在构建完成前就重开测了旧二进制，会把上轮的修复
  当成"没改"）。纯函数体改动可提示 Live Coding（Ctrl+Alt+F11）热补，动了类成员/反射就必须冷编译重启。
  只重启、仍加载旧 DLL，再读旧档，木材会继续是旧图标和 1×1。

## 背包拖拽：装备栏旋转与拖到仓库换装（2026-09-24）

- 拖拽中按 F 的来源包括背包（Place 0）、装备栏（Place 1）和仓库/箱子（Place 4）。朝向只在落点是背包或仓库时写入；装备槽放下仍用作者朝向。
- “可旋转”预览只在悬停背包或仓库、且来源是 0/1/4 时打开。从装备栏拖到背包或仓库可以转；悬停装备槽不要提示可转。
- 从装备栏拖到仓库时，落点锚格上、能装备进空出槽位的那件换上；覆盖到的其余物品进背包。背包放不下则整次移动取消。预览文案是“松开替换装备”。双手武器换上时副手按现有规则进背包，进不去就中止这次装备。
- 仓库堆叠合并的余量必须带回源容器和源宽高。余量若先改掉 `Container` 再提前返回，箱子里的物品会变成主仓库物品。

## 运行时图标与诊断界面开销

处理动态图标首次准备卡顿、图标通知全量刷新或诊断文本反复失效时，读取 [运行时图标准备](references/runtime-icon-pipeline.md)。
