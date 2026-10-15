# 力量符文

通用符文 `strength_rune`，物理伤害 **+10%**。数值使用既有 `physical_damage_mult: 1.1`，与其他物理倍率按现有系统相乘，不增加火焰伤害或其他未指定属性。

图案为原创中轴重印：粗壮中央笔画、两组向内折转的肩纹、两侧独立菱形及底部收束尖角。完整贴附纹样用长轴刻纹与错落短折纹衔接主印。实战为赤红色，使用已有渐隐和流光时序。

## 制作源

- `author_assets.py`：同一多边形源生成可编辑 SVG、灰度遮罩和红色设计图，不从图标反推实战纹样。
- `strength_rune_mask.svg`：1024 × 4096 可编辑遮罩源。
- `T_Mask_strength_rune.png`：实战读取的遮罩；灰度、非 sRGB、保留纹理流送。
- `StrengthRune_Design.png`：用户请求的红色图案设计展示，左侧核心符印、右侧完整纹样；不是游戏截图。
- `StrengthRune_CoreReference.png`：金属框图标的准确轮廓参考。
- `blade_2_strength_rune.png`：内置 imagegen 制作的灰白浮雕共享图标，沿用既有共鸣符文金属框。
- `icon-generation.json`：完整图标提示词及参考图。

## 接入

数值与说明唯一来源为 `Content/ColdSteelData/melee-gunsmith.json` 的 `blade_2` 通用选项；剑类直接使用，金属战锤通过现有 `rune` 列引用同一目录。`ColdSteelFrostRunes::IsCommon` 接纳该 ID，存档沿用原有部件字段及归一化流程。

`MeleeRuneVisual.cpp` 复用通用模式 2 的纹样投射与流光，设置独立红色调色参数；切换回导魔时恢复父材质颜色，急速仍为黄色。已有东方剑身原生材质与常规叠加材质均使用同一入口。战锤继续使用 ShaftWrapV2 的实际弧长映射、原尺寸与柄部覆盖区间，无需移动或缩放符文。

UI 共享键 `blade_2_strength_rune` 已由战锤的符文槽别名支持，不增加每把武器的图标副本。资源沿已有按配方收集与缓存路径加载；不增加 Tick、纹理轮询或伤害分支。

`import_assets.py` 实际保存两张 UE 纹理后再执行 `register_rune.py` 登记选项。导入使用一次纹理设置批次；配置变更前保留 `Before` 备份，后续重导外观保留同 ID 已调整的数值。

默认不启动或关闭用户编辑器。本轮经现有编辑器桥保存资产；编译及保存结果在本目录回执中。未启动游戏、运行自测或进行实机验收，交由用户测试。
