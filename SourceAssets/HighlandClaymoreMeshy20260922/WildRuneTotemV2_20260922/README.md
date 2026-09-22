# 蛮荒符文 V2：兽颚破甲战纹

用户要求重做原先单一、重复的符文样式。本轮只修改高地双手剑 `wild_rune` 的视觉与描述；韧性伤害 +30%、物理防御穿透 +20% 及改造兼容范围保持原值。

## 设计

一条完整的非平铺战纹：护手附近为较大的兽颚主印，中部为长斜爪痕、短钩裂痕和断开的横切印，剑尖方向收束为细长骨矛。破碎剑脊连接各段，保持不等距、不同笔画粗细及留白，取代 V1 六组同形符号。

使用暗红刻痕、局部猩红亮纹与少量温红脉动。主印略亮，其他位置依剑身高度产生不同相位，边缘通过小范围采样光晕渐隐。原模型固有符文在安装蛮荒符文时降为低亮度红色底纹，其他改造不受本分支影响。

## 制作来源与复现

- 通过内置 imagegen 生成全新黑白发光遮罩，完整提示词在 `imagegen_prompt.txt`。
- 生成原图原样复制到 `Textures/T_WildTotem_Generated.png`，未裁切、重绘或调色。黑白只是材质覆盖数据，游戏颜色由 shader 提供。
- `package_art.py` 只读取覆盖范围，记录用于贴合的 UV 矩形；实际横转竖及取景由 `wild_totem_v2.hlsl` 完成。
- `production.json` 记录源图、采样范围、色彩和参数。原图横向骨矛朝左，兽颚朝右；映射到剑身后，骨矛朝剑尖，兽颚朝护手。
- 语义图标继续使用既有破甲獠牙图标；本轮未重做图标、剑模型或任何玩法代码。

## 接入

通过 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript .../install_totem.py` 修改现有资产，保留运行引用：

- `/Game/Weapons/HighlandClaymore20260922/WildRune/T_Mask_wild_rune`
- `/Game/Weapons/HighlandClaymore20260922/WildRune/M_SilverRuneSurface_HighlandWild`
- `Materials/M_HighlandClaymoreSurface` 和 `_Whirlwind` 的 `NativeWild` 条件分支。

材质参数 `ArtUVRect` 经 AppendVector 显式拼接 RGB 与 A，向 Custom HLSL 传递四分量矩形；VectorParameter 未命名输出仅为 RGB。

`Before/` 保留替换前二进制、shader 与目录；`install_receipt.json` 记录保存结果。旧 `WildRune20260922` 为 V1 作者源，重跑其安装器会恢复旧视觉；当前修订以本目录为准。

已完成资产保存与必要材质编译。无需 C++ 构建；未启动游戏、截图、额外渲染或测试，由用户体验。
