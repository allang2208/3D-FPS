# 统一 E 交互小浮窗（2026-09-24）

## 用户指令
任何交互统一调整为高炉、工作台的小浮窗模式；不再显示模型上方的名称和 E 键交互提示；
浮窗背景改毛玻璃灰黑色、字体白色。E 键行为不变（仍是 E 打开对应面板）。

## 改动前现状
- **准星小浮窗（即时绘制）**：仅 高炉 / 工作台 / 探险宝箱 / 出征祭坛 四类
  （`ColdSteelCrosshair.cpp::NativePaint` 一段 MakeBox+MakeText，背景为不透明深灰 `Tooltip`）。
- **模型上方世界空间名牌**（要废除的对象）：
  - 仓库宝箱与五档储物箱：`UColdSteelChestPrompt`（`E · 武器仓库` / `E · 木质储物箱`…）
  - 拾取物：`AColdSteelPickup::Prompt`（`E · 拾取 X ×N`，Tick 里按聚焦显隐）
- 生产工具（斧/镐/铲）底部提示为视口浮窗（`ProductionToolComponent::UpdateHint`），
  不在模型上方、内容是按键说明而非 E 交互提示——保持原样。
- 门：原本准星命中**无任何提示**（E 静默开关）——并入统一浮窗（`门 · 开／关`）。

## 方案落地
1. **统一文案源**：`ColdSteelWorldInteraction::ResolveInteractionHint(Actor)` →
   `{ FString Text; bool bAction; }`。分派顺序与 E 键处理一致：祭坛→宝箱→仓库箱/储物箱
   →拾取物→高炉→工作台→门。空文本＝不显示；`bAction=false`（已开启/锁定的宝箱）只显示状态、
   隐藏 E 徽标。
2. **毛玻璃浮窗**：`UColdSteelHUDWidget::BuildInteractHint/UpdateInteractHint`——
   `UBackgroundBlur`(强度9/半径21，与全项目玻璃面板同一配方)＋`UBorder(GlassTint=Gray26/α248 灰黑)`
   ＋圆角 CardRadius；内容行 = 白色加粗 `E` 徽标 + 白色正文；锚点屏幕中心、准星下方 56px、
   自动尺寸（长文本自适应）。`NativeTick` 驱动，文本/徽标仅在变化时 Set（不做每帧 SetText）。
   出现条件与旧即时提示一致：背包/仓库开着、光标显示、弹药轮、命中反馈期间不显示。
3. **拆世界名牌**：
   - `AColdSteelWarehouseChest`：删除 `UColdSteelChestPrompt` 类、`Prompt` 组件与 BeginPlay/Tick 挂接；
     `GetPromptLabel()` 语义改为浮窗正文（无 `E · ` 前缀）：基箱 `武器仓库 · 打开仓库面板`，
     储物箱 `<档位名> · 打开储物面板`（子类覆写同步）。
   - `AColdSteelPickup`：删除 `Prompt` 组件；`InitializeItem` 存 `PromptCaption=拾取 X ×N`，
     经 `GetPromptText()` 供解析器读取。
   - `ColdSteelCrosshair.cpp`：删除旧即时绘制块（单一渲染路径，避免双提示）。
4. **不触碰**：E 键分派（`FPSGAMEPlayerController::InputKey` 原顺序）、各面板逻辑、
   高炉/工作台/宝箱面板本体（已是 GlassTint 毛玻璃＋浅字）。

## 验证与状态
- UBT 编译记录：`SourceAssets/WarehouseCrateTiers20260924/build_unified_hint.log`
  （编辑器开着时链接会被锁——编译过、待关编辑器后完成链接交付）。
- 未做游戏内实测（用户规则）：预期行为＝注视仓库箱/储物箱/拾取物/门/高炉/工作台/宝箱/祭坛时，
  准星下方出现同一只灰黑毛玻璃白字浮窗；模型上方不再有任何名牌。
