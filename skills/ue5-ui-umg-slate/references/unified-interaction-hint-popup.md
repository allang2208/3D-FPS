# 统一 E 交互小浮窗（FPSGAME，2026-09-24 定版）

一切 E 交互提示统一走准星下方毛玻璃小浮窗；模型上方不挂世界空间名牌（用户定版口径）。
落地记录见 `Docs/UI/unified-interaction-hint-20260924.md`。

## 结构合同
- **唯一文案源**：`ColdSteelWorldInteraction::ResolveInteractionHint(AActor*)` →
  `{FString Text; bool bAction;}`；分派顺序必须与 `AFPSGAMEPlayerController::InputKey` 的
  E 键处理顺序一致（祭坛→宝箱→仓库箱/储物箱→拾取→高炉→工作台→门），否则"显示即可用"失真。
  空文本＝不显示；`bAction=false`（只读态，如已开启/锁定宝箱）隐藏 E 徽标只留状态。
- **文案不带 `E · ` 前缀**（徽标由浮窗自绘）；箱类正文走虚接口
  （`GetPromptLabel()`），储物箱子类按档位覆写，新增容器零浮窗改动。
- **渲染层**：`UColdSteelHUDWidget::BuildInteractHint`（构造于 `BuildInterface`）+
  `UpdateInteractHint`（`NativeTick` 驱动）。必须用真控件（`UBackgroundBlur`）而不是
  `NativePaint` 的 `MakeBox`——即时绘制拿不到背景模糊，毛玻璃只在控件树里成立。
  旧即时绘制路径已删除；不要再引入第二条提示渲染路径（双提示/漂移的根源）。
- **出现条件与旧准星提示逐字对齐**：任一面板打开、`bShowMouseCursor`、弹药轮、命中反馈期间不显示；
  改条件时两处（若还有其它消费者）一起改。

## 玻璃配方（与全项目面板同源，ColdSteelUI）
`UBackgroundBlur(GlassBlurStrength=9, GlassBlurRadius=21, auto-radius, corner=ReferenceUnits(CardRadius),
LowQualityFallbackBrush=RoundedBrush(GlassFallback))` → `UBorder MakeSurface(GlassTint=Gray(26,248),
ReferenceUnits(CardRadius), Border, ReferenceUnits(1))` padding(12,7) → `UHorizontalBox[白色加粗"E"
(16px, NumberFont)][正文白色(15px)]`；画布锚 (0.5,0.5)、对齐 (0.5,0)、下偏 ReferenceUnits(56)、
AutoSize、ZOrder 38（在面板之下：面板开着时本来就不出现）。

## 性能与刷新纪律
- 每帧只做一次 `TraceTarget` 线trace（250）＋字符串比较；`SetText` 仅在文本变化时调用；
  徽标可见性用 `bLast…` 缓存 bool 守卫。禁止每帧无条件 SetText（文本键重建 invalidation）。
- 撤除世界名牌时把文本降级为 actor 上的 `FString`（如 `PromptCaption`）/虚函数，
  删掉组件创建、`InitWidget`、Tick 里的 `SetWorldLocation/SetVisibility`。

## 构建闸门（本轮实测）
删 UCLASS、增删 UPROPERTY/组件属**结构性改动**：Live Coding（Ctrl+Alt+F11）应用不了，
UBT 在编辑器运行期直接拒绝（"Unable to build while Live Coding is active"）——
交付时先如实报告"编译被编辑器挡住的哪一步"，由用户关编辑器后整编，不擅自结束用户进程。
