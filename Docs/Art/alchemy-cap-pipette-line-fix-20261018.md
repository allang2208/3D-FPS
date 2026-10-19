# 炼药台细线：RedRoot 长提取管

> **2026-10-19 降级：提取管不是这条线。** 四款试剂盖源模型量得最长提取管 10.8 cm（RedRoot），经 `IngredientRest` 缩放后 13–18 cm，在 1–2 m 处最多投影约 40–100 px，而截图中的线长 600+ px，差一个数量级。并且 `AnimateIngredients` 只让瓶盖绕 Z 轴旋转，**提取管始终保持竖直**，不可能产生截图中那条斜穿全屏的斜线。本隐藏修复保留（瓶盖抬升时确实难看），但不能作为线源结论。见 [第三轮复排](alchemy-gold-line-third-audit-20261019.md)。

日期：2026-10-18
范围：投料/倒药水时，从瓶口斜穿坩埚和桌面的金色/米色细线。

## 结论

这条线是 **RedRoot 瓶盖带的长提取管（cap / extraction pipette）**，不是模型接缝、hover 描边，也不是枪械镭射。

![实机：线从倾斜瓶口出发](../../SourceAssets/PotionWorkbenchDesign20261015/SeamFix20261017/UserReport/user_cap_line.png)

`SM_AlchemyRedRootCap` 的包围盒：

- x/y：±1.43 cm
- z：1.20–12.01 cm
- 长度约 **10.8 cm**，直径只有约 **2.9 cm**

盖子在倒料动画里被抬起、旋转并停到瓶口旁，但它的长提取管仍作为细圆柱显示。玻璃/铜件在阳光和透明材质下几乎只剩一条 1–2 px 的高光边，看起来就像一条从瓶口一直划到桌面的“不明细线”。

![RedRoot 盖渲染：主体就是一条长管](../../SourceAssets/PotionWorkbenchDesign20261015/SeamFix20261017/FixedRenders/redroot_cap.png)

## 修改

1. `AlchemyTransferVisual.cpp` 的 `AnimateIngredients`
   - 记录瓶盖的 `Open` 因子；
   - 当瓶盖抬起超过 0.82 后，把该瓶盖的组件隐藏；
   - 倒料结束、瓶盖回落时重新显示。
2. `AlchemyTabletopInteraction.cpp` 的 `UpdateIngredients`
   - 状态每帧/每次复制刷新时会把所有瓶盖重新设为可见；
   - 现在对“正在倒的瓶子”跳过这个重新显示，避免瓶盖被状态刷新重新弹出。

这只隐藏被倒容器的瓶盖，不影响其他瓶子、瓶盖回收动画、库存、配方或网络状态。

## 为什么不是前两次的判断

- **不是模型接缝**：底环/勺头在离线几何里确实有互穿，但已经清理；这条线是从瓶口发出的独立零件。
- **不是枪械镭射**：镭射也由独立世界组件渲染，确实是一个真实隐患；已加入 `HiddenActors` 隐藏并保留该修复，但它不是截图里从瓶口出发的这条线。
- **不是 hover 描边**：hover 改动已回滚，UI 仍保留金边提示；这条线在瓶子没有被 hover 时也会出现。

## 构建

- Game：`Saved/BuildGame/build-20261018-003522.log`，`Result: Succeeded`
- Editor：`Saved/BuildEditor/build-20261018-004455-after-editor.log`，`Result: Succeeded`
- 中途 `build-20261018-003610.log` 因编辑器占用 DLL 链接失败；未关闭编辑器，等它退出后自动补建成功。现在的最新 Editor DLL 同时包含瓶盖隐藏和 `UpdateIngredients` 防重显保护。

## 边界

- 没有 PIE/游戏内视觉验收。
- 当前编辑器已关闭，最新 Editor DLL 已落盘；重开编辑器后生效。
- 如果还有线，先确认它是否仍从瓶口出发、长度约 10 cm；若是，说明还有其他长管/细杆组件（例如别的试剂盖或舀勺手柄）没有隐藏。
