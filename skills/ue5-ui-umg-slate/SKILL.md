---
name: ue5-ui-umg-slate
description: Plan and implement UE5.6-UE5.8 panels, tabs, sections, cards and popups using UMG and Slate. Use for new UI or UI upgrades, FPSGAME Cold Steel design rules, panel/column workflows, Widget Blueprint setup, lifecycle binding, data visibility, input/focus, tooltips and viewport layout.
---

# Quick Start
- For FPSGAME new panels, tabs, sections, cards, or UI upgrades, first read [panel planning and Cold Steel rules](references/fpsgame-panels.md). Plan structure, layout, data scope and states before implementation; use the project's current design system.
- For FPSGAME inventory drawers, detached item menus, or drag/close regressions, read [inventory input and validation](references/fpsgame-inventory-input.md).
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
