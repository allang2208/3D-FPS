# 图鉴入口图标 2026-09-27

用户要求生成并替换右侧缺失的图鉴图标。

- 生成方式：OpenAI 内置 imagegen，transparent_background=true。
- 成品：Content/ColdSteelUI/Icons/Navigation/codex_subject.png。
- 接入：ColdSteelPanelNavigation.cpp 既有第四入口已引用该文件；LoadUiTexture 直接导入 PNG。现有 DefaultGame.ini 已暂存 Navigation 目录，无需添加 uasset、修改 C++ 或编译。
- 黑色皮革合本图鉴、旧银怪物徽记、少量暗金饰边，与现有打开的技能书区分。沿用现有尺寸、悬停效果和 N 快捷键。
- 未启动编辑器或进行运行测试。下次构建 HUD 时读取新资源。

## Generation prompt
Create one production game HUD inventory navigation icon, square composition, isolated on true transparent background. A CLOSED upright thick bestiary encyclopedia tome in three-quarter front view, centered filling 88% of canvas, dark charcoal leather, worn cold silver metal protective corners and spine, a prominent sculpted silver horned monster skull medallion on the front cover and very restrained antique muted gold fine edging. This represents the encyclopedia of monsters and weapons. Realistic sculpted 3D game item rendering, sharp readable silhouette at 72px, strong light silver highlights and dark cavities, match a cold steel HUD set with silver character bust, backpack and an open silver skill book. Distinguish this icon by using a CLOSED book and monster emblem, not an open spellbook. Neutral studio lighting, no bright magic, no glow, no pedestal, no ground shadow, no surrounding panel or frame, no text, no letters, no hotkey, no watermark. Transparent surrounding and cutout silhouette. Save as PNG.
