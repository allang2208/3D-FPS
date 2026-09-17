# 法术弹道预览（悬浮长按 → 松手发射）

2026-09-17 在火球与冰锥上落地的通用做法。新法术接入时照这套走，不要再各写一份。

## 输入契约

- **点按发射；悬浮时长按显示预览，松手才发射。** 快速点按＝按下进预览、抬手瞬间发射，观感与「按下即发射」一致。
- 凝聚（gather）期间按下保持原语义：排队一次发射／齐射请求，不进入预览——否则第一下按键会被吞掉。
- 菜单（背包／枪匠／附魔／建造／破防）会吞掉按键抬起，`AFPSGAMECharacter::SuspendWeaponForMenu()` 必须清掉预览；释放分支除索引外还要校验该法术的 `IsAimPreviewActive()`，否则预览随投射物消失后仍会触发一次施法。
- 世界交互键（E）优先级不变：交互判定仍在快捷槽之前。
- 接线：`AFPSGAMEPlayerController::InputKey`（按下 → `BeginSpellAimPreview`，抬起 → `EndSpellAimPreview`）→ `UColdSteelStatusModel` → 法术组件的 `SetAimPreview/IsAimPreviewActive` → 投射物／volley 的 `SetAimPreviewActive` + `RefreshAimPreview`。

## 弹道预测必须与飞行同源

- 飞行用**解析弹道**：`位置 = 起点 + 初速×t + ½×重力×t²`（帧率无关）；初速方向指向准星射线命中点。
- `FPSMagicPreview::SamplePath()` 用同一积分（固定 1/60 秒步长、最多 48 点）采样，逐段球形扫掠（火球 14 cm、冰锥 18 cm，与各自飞行一致），命中即截断，**已倒下的尸体继续穿过**、墙体与活体敌人停下。
- 重力数值放 `skills.json` 的 `gravity`（cm/s²），现场用 `fps.Magic.GravityScale` 缩放（0 = 直线飞行）。改了重力必须同时改预测，否则线会骗人。

## 绘制要点（批量线段的坑）

- 用投射物／volley 自己的 `ULineBatchComponent`，`BeginRefresh()` 每帧先 `Flush()` 再画：线段寿命 0（持久）+ 每帧重建，转视角才不会留下几帧旧线叠成拖影。
- **混合机制（2026-09-17 实锤，勿再猜）**：`ULineBatchComponent` 的厚线段（Thickness > 0）走 `FViewElementPDI::DrawLine → FBatchedElements::AddTranslucentLine`，绘制批以 **`SE_BLEND_AlphaBlend`** 合成：`Dst.rgb = Src.rgb×Src.a + Dst.rgb×(1−Src.a)`（`BatchedElements.cpp` 的 `SetBlendState` 与 `SimpleElementPixelShader.usf` 均已核对）。**alpha 有效，淡出／变透必须挂在 alpha 上，RGB 保持满强度**。压 RGB 而 alpha 恒 1 得到的是不透明暗红线，盖在背景上读成阴影而不是淡出（2026-09-17 第三轮近端淡出因此失败）。注意区分：`PostProcessCompositeDebugPrimitives` 的 `BF_One/BF_One` 加法合成只适用于 `DrawDebugLine` 那类调试 PDI 路径，不是本组件的路径。
- **不要叠宽而暗的“柔光带”**：深色半透明宽线在 alpha 混合下会把背景压暗，看起来是一圈粗阴影而不是辉光（2026-09-17 实测踩过，已彻底移除叠加带）。
- 虚线断点按**累计弧长**推进（`fps.Magic.PreviewDashCM`／`PreviewGapCM`），不要按采样点分段，否则断点会随采样密度变化。
- 近端（贴法术那一端）在路径前 32% 内**alpha 从 0 渐升**并略细，远段保持满强度满 alpha 单线；给整条线统一降透明度会被读成“整条线都被改了”。

## 配色与状态

- 线色为满强度红 `(0.95,0.12,0.08)`，写满 alpha；端部淡出只乘 alpha 不动 RGB（机制见上节）。
- 冷却、缺蓝、左手占用等状态仍走原快捷槽通道（`StatusText()` / `FFPSLeftHandNotice`），预览线不承担这些信息。
