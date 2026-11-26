# 炼药 hover 金边细线排查（2026-10-17，已回滚）

> **2026-10-18 更正：本文结论错误。** 最终确认线源是 [RedRoot 瓶盖长提取管](alchemy-cap-pipette-line-fix-20261018.md)，不是 hover 描边，也不是镭射。本文的 `SetHoverTarget` 改动已回滚，`金边器具可操作` 提示也已恢复。

## 原判断（已否定）

实机截图里的细线曾被判断为**金色 hover 描边**；该判断没有解释“枪隐藏后线仍在”和“线从空中枪口位置发出”。

![用户截图：瓶身和长柄上的金色细线](../../SourceAssets/PotionWorkbenchDesign20261015/SeamFix20261017/UserReport/user_gold_lines.png)

## 原因

`UPotionWorkbenchVisualComponent::SetHoverTarget` 对 `Bottle` 同时加入 **Dose + Ladle**，对 `Ingredient` 同时加入 **瓶身 + 瓶盖**，对 `Stirrer` 加入整根长勺。hover 描边用 **custom depth + stencil 229** 做外轮廓；这些对象不是单一闭合体：

- Dose：玻璃量瓶 + 铜颈环 + 4 圈容量刻度；
- 配料瓶：玻璃瓶 + 底环 + 液体 + 标签 + 12 个蚀刻刻度；
- Ladle/Stirrer：长柄 + 勺头/勺斗 + 握柄环 + 杆头接缝。

每个独立零件/薄片都会在 stencil 里形成自己的轮廓，描边就会沿瓶身刻线、铜环和长柄生成多条**1–3 px 的金色细线**，看起来像“不明线条”。截图里瓶身的多圈环线和横穿桌面的长线分别对应 Dose/Ladle 零件和多零件瓶身。

## 修改

- `Source/FPSGAME/Building/AlchemyTransferVisual.cpp`
  - `SetHoverTarget` 对 **Ingredient / Bottle / Stirrer** 不再生成 hover 轮廓；仍保留悬停名称、操作说明和手型光标。
  - 其余对象（书、火力旋钮、研钵、沙漏、液面）继续使用金边描边。
- `Source/FPSGAME/UI/ColdSteelAlchemyWidget.cpp`
  - 底部提示从“金边器具可操作”改为“悬停器具可操作”，避免对已取消金边的瓶子/勺子做错误承诺。
- 未改模型、材质、配方、库存、存档或网络。

## 构建

- Game：`Saved/BuildGame/build-20261017-231023.log`，`Result: Succeeded`
- Editor：`Saved/BuildEditor/build-20261017-231607.log`，`Result: Succeeded`
- 没有打开可见编辑器，没有 PIE、游戏内视觉或联机验收。

## 验证建议

进炼药台后：

1. 悬停配料瓶：不应再出现瓶身金环和横穿场景的金线；仍应看到名称/操作浮窗和手型光标。
2. 悬停 Dose/长柄舀勺：不应再出现量瓶刻度环和长柄金线。
3. 悬停搅拌勺：不应再出现长柄/勺头金线。
4. 书、火力旋钮、研钵、沙漏、液面仍应有金边；如果没有，说明描边被整体关闭，而不是按对象关闭。

若仍有细线，重点看颜色：
- **金色**：可能来自上述未覆盖的对象，或描边材质/后处理；
- **白色/蚀刻色**：是瓶身标签/刻度面片，不是 hover；
- **暗/亮色**：是模型接缝或硬边，回到[接缝审计](alchemy-prop-seam-audit-20261017.md)。
