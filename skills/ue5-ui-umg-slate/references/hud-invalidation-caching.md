# Cold Steel HUD InvalidationBox 缓存与防击穿规范

提炼自 `HillsPerfOpt-R56` ～ `R57` 对 `UColdSteelHUDWidget` 家族的性能排查与实测经验。适用于在 `UE 5.6–5.8` 中使用 `UInvalidationBox` 包裹复杂 UMG HUD 的全部面板、仪表与文本读数。

---

## 1. 架构隔离：`UInvalidationBox` + 独立叶子绘制层

不要在主 `UColdSteelHUDWidget::NativeTick` 中每帧对整棵 WidgetTree 触发 `Invalidate(Paint)`；任何每帧变化的准星、罗盘、导航标记、受击指示、弓镜光学遮罩都必须拆离缓存箱：

1. **三层结构**（保留 `WidgetTree->RootWidget` 为 `UCanvasPanel`）：
   - **底层叶子绘制** `BackPaintOverlay`（`UColdSteelHUDPaintLayer`，`Z = -100`）：负责弓镜/开镜光学全屏遮罩，仅在瞄准激活或刚退出那一帧局部 `Invalidate(Paint)`。
   - **主缓存箱** `HUDInvalidationBox`（`UInvalidationBox` 包裹 `ColdSteelRoot`，可控开关 `fps.HUD.InvalidationCache=1`）：承接血蓝条、生存条、快捷栏、武器读数、世界时钟、天气时间轴、交互提示与抽屉面板。
   - **顶层叶子绘制** `FrontPaintOverlay`（`UColdSteelHUDPaintLayer`，`Z = 200`）：负责每帧更新的准星、罗盘刻度、标记与目标血条框，仅对其自身 `CachedWidget->Invalidate(Paint)`。

---

## 2. 缓存防击穿清单（实测极易泄漏 `UInvalidationBox` 的写法）

`UInvalidationBox` 内部任意子控件只要无条件调用 Slate setter（即便传入与当前完全一致的文本、颜色、坐标或显隐），都会标记缓存脏并在当帧重建整棵 HUD 的 Slate Geometry / DrawElements（`Slate_PaintSlowPath` + `HUDInvalidationCache` 尖峰）。高频刷新与 `Tick` 路径必须遵守：

- **文本与颜色必须双守卫**：
  - `UTextBlock::SetText` 前比较缓存字符串或 `GetText().ToString() != NewValue`；仅文本判重**不够**，`SetColorAndOpacity`、`SetFont`、`SetWrapTextAt` 同样无条件标脏，需按控件指针维护颜色/字体状态缓存（参考 `UColdSteelAmmoReadout::SetTextIfChanged` / `SetColorIfChanged`）。
- **显隐与槽位布局必须判重**：
  - `SetVisibility` 前检查 `Widget->GetVisibility() != DesiredVis`（如 `UpdateInteractHint()` 中的 `InteractHintBlur`/`InteractHintTitle`、`RefreshAmmo()` 抽屉折叠时的 `AmmoReadout->SetVisibility(Collapsed)`）。
  - `UCanvasPanelSlot::SetAutoSize` 只在初始化设一次；`SetPosition` / `SetSize` 使用 `FVector2D::Equals(Target, 0.05f)` 比较后写入。
- **画刷 / Tooltip / 按钮样式不能周期性无脑覆写**：
  - 类似 `RefreshEventTimeline`（0.25 s 周期）内 `ColdSteelToolTip::Set`、`SetBrushFromTexture`、`SetBrush`、`UpdateEventTimelineFilterButtons`（每周期重建 `FButtonStyle` 并 `SetStyle`）都会每周期击穿整盒缓存，必须用轻量可视化缓存结构比对后再写。
- **连续量必须做视觉精度量化 + 边界穿透**：
  - **世界日晷指针**：连续 `NormalizedDayTime` 精确比较会令 20 Hz 刷新次次重绘 `< 0.01°` 的表盘；量化为每日 `720` 步（`0.5°` 步进）即可兼顾流畅与静止帧 0 重绘。
  - **资源条/生存条**：饥饿/水分/SAN 等持续缓慢衰减数值用精确 `Value == Next` 判重会导致每 `0.05 s` 唤醒 `RegisterActiveTimer` 连刷数帧；在 `UColdSteelResourceMeter::SetValue` / `SetSemanticValue` 使用 `0.0025f`（`< 0.3 px`）死区，同时对 `<= 0`、`<= 0.25` 预警线与 `>= 1` 状态阈值保留即时穿透。
  - **慢速时间轴位置与闲置呼吸**：时间轴标记位移使用 `>= 0.002f` 阈值（临近触发点 `<= 0.041f` 保留即时吸附），阻止每日进度小数微漂反复重启 `0.18 s` 位移动画；折叠待机期仅预览未来事件时不跑高频 `SetRenderOpacity` 呼吸脉冲，保持稳态透明，仅进行中/展开态节流脉冲（`0.15 s` / `>= 0.03`）。

---

## 3. 模型派生数值与组件指针缓存

- **派生数值版本键缓存**：在 `UColdSteelStatusModel` 中，将静态装备加成与资源上限按复合版本键（`StatCacheVersion + Generation + Level + ActiveWeaponSlot + Items.Num() + Infection.Stage + bSanityDepleted`）缓存 `EquipmentBonus`、`Derived("maxHp"/"maxMp")` 与 `AdjustedManaCost` 乘区，去除热路径内层堆上 `TArray` 临时分配；任何修改 `Current.Items`/`Attributes`/`Survival`/`Infection`/`Skills` 的入口确保递增 `StatCacheVersion`。
- **Pawn 组件指针缓存**：`RefreshQuickBar`、`RefreshTopVitals`、`UColdSteelAmmoReadout` 与 `BackPaintOverlay` 等 20–60 Hz 调用方按 `TWeakObjectPtr<const APawn>` + `GetComponents().Num()` 缓存组件指针，避免每帧重复遍历 Actor 组件列表执行 `FindComponentByClass`。

---

## 4. 源码参考入口（相对 `FPSGAME.uproject`）

- 主框架与叶子层：`Source/FPSGAME/UI/ColdSteelHUDWidget.h/.cpp`、`ColdSteelCrosshair.cpp`
- 面板/读数/时间轴/时钟/仪表守卫：`ColdSteelHUDConstruction.cpp`、`ColdSteelHUDReadouts.cpp`、`ColdSteelAmmoReadout.h/.cpp`、`ColdSteelStaffReadout.cpp`、`ColdSteelWorldClock.cpp`、`ColdSteelHUDTimeline.cpp`、`ColdSteelEventTimeline.cpp`、`ColdSteelResourceMeter.cpp`
- 状态与法力乘区缓存：`ColdSteelStatusModel.h/.cpp`、`ColdSteelProfileRuntime.cpp`、`Skills/ColdSteelSpellMana.cpp`
