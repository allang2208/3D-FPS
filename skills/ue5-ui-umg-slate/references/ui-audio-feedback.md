# 全界面按钮、栏位与组件交互音效规范（ColdSteelUIAudio）

2026-11-27 落地，源码入口：[ColdSteelUIAudio.h](../../../Source/FPSGAME/UI/ColdSteelUIAudio.h) · [ColdSteelUIAudio.cpp](../../../Source/FPSGAME/UI/ColdSteelUIAudio.cpp)。复用迁移自原项目 `gamedev` 的 `/Game/Audio/GamedevUI20261002/S_Button_Click`（已写入 `Config/DefaultGame.ini` 的 `DirectoriesToAlwaysCook`）。

## 1. 架构原则：单子系统预载 + 视口限定 Slate 拦截，不改 `ColdSteelUIStyle.h`

- **不要在各按钮 `OnClicked` 里散落 `LoadObject`**：统一由 `UColdSteelUIAudioSubsystem`（`UGameInstanceSubsystem`）启动预载 `ButtonClickSound`，避免每次点击触发同步查找，同时跳过 Commandlet、独立 Dedicated Server 与编辑器内置 DS PIE（`IsDedicatedServerInstance()`）。
- **不要改动 `ColdSteelUIStyle.h` 加 `PressedSlateSound`**：该头文件被上百个 UI 文件包含，改动会触发全量重编译，且无法覆盖大量手写 `FButtonStyle()` 的按钮，还容易与手动 `PlayButtonClick()` 双响。
- **使用游戏视口限定的 `IInputProcessor`**：自动覆盖全项目所有启用态的 `SButton` / `UButton` / `UColdSteelMountButton` / `SCommonButton` / `SExpeditionButton` / `SComboButton` / `UComboBoxString` / `SCheckBox` / `SMenuEntryBlock` / 下拉列表行（含快速连击 `HandleMouseButtonDoubleClickEvent` 与键盘 `Enter`/`SpaceBar`）及 `SSlider`。
- **以 `bIsUISound = true` 播放**：确保单人暂停菜单（`SetGamePaused(true)`）下按钮照常发声。

## 2. 必须守住的五个边界与性能约束

1. **严格隔离 UE 编辑器 UI**：
   - 仅当命中路径包含当前 `GameInstance` 的 `GameViewportWidget` 时放行，并置位游戏下拉菜单授权标志 `bGameMenuOpenedFromViewport`。
   - 凡点击落在游戏视口外且非 `EWindowType::Menu` 窗口，立即撤销授权，杜绝点击编辑器工具栏或菜单时漏响游戏音效。
2. **FPS 战斗期 O(1) 零遍历快返**：
   - `HandlePointerPress` 必须**在 `SlateApp.LocateWindowUnderMouse(...)` 之前**做快返：非左键且无弹窗授权直接返回；左键且本地 `PlayerController->ShouldShowMouseCursor() == false` 且无可见弹出菜单时直接返回，避免开火/举镜遍历整棵 HUD Slate 树。
   - `Tick` 中一旦光标收起或弹出菜单关闭即复位 `bGameMenuOpenedFromViewport`。
3. **键盘拦截必查可见性与可交互链**：
   - `HandleKeyDownEvent` 必须同时校验无光标局内跳过 + 焦点控件 `IsHitTestVisible()` + 沿视口到焦点的完整路径满足 `IsEnabled() && GetVisibility().IsVisible()`，防止面板折叠/隐藏后残留焦点导致局内按空格跳跃误响。
4. **防抖与旧 `PlayButtonClick()` 释放去重**：
   - 统一 45 ms 播放节流；拦截器在 `MouseDown` / `MouseUp` 登记按压与释放时间，旧 `UColdSteelHUDWidget::PlayButtonClick()` 走 `PlayLegacyButtonClick()` 在 120 ms 窗口内去重，兼顾鼠标点击防双响与程序/快捷键调用有声。
5. **非按钮栏位三档分级与有效落位校验**：
   - `Button`（音量 `1.0` / 音高 `1.0`）：按钮、页签、下拉选项、整理按钮、右键快捷操作、商店双击确认。
   - `Slot`（音量 `0.78` / 音高 `1.06–1.12`）：背包/仓库/快捷栏/商店/技能树/魔法轮盘/地图标记/种植田块/焚化炉弹药/强化台抓取/NPC 对话推进/滑条按下。
   - `SlotDrop`（音量 `0.85` / 音高 `0.92–0.97`）：拖拽成功落位、装备、出售、马具装上、强化置入。
   - **错位拖放不播成功音**：如马具槽（`ColdSteelMountGearPanel::HandleItemDrop`）须先校验来源容器与 `StableHorseGear::SlotOf(...) == SlotIndex` 再播 `SlotDrop`；背包/快捷栏仅在操作返回成功时播 `SlotDrop`。
   - **保留专用音效不覆盖**：枪匠确认（`S_Gunsmith_Confirm`）、炼金书翻页（`SW_AlchemyPage`）、木工锯与枪械装配碰撞音保持独立，不在其自定义命中面叠加通用点击音。
