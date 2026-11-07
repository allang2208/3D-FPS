# 玄脊碳纤维枪托图标替换

用户批准将最新生成的碳纤维材料徽章接入为该配件图标。`Selected.png` 是批准图的原样副本，未重新生成或修图。

- 实际 UI 图标：`Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/ue_m24_stock_m24_carbon_spine_stock.png`
- 兼容图标：`Content/ColdSteelData/AttachmentIcons20260913/ue_m24_stock_m24_carbon_spine_stock.png`
- 两个同名 UE Texture2D 资产由 `install.py` 导入并保存。
- `Before/` 和 `baseline.json` 保留此次替换前的四个文件及散列。
- 纹理使用 UI 分组、Editor Icon 压缩、sRGB 和 Never Stream。
- 执行结果以 `installed.json` 的 `complete` 和 `assets_saved` 为准。

本次仅替换图标，不涉及模型、配件数值或 C++。不主动启动编辑器或游戏，不进行游戏内测试。已运行游戏中的图标缓存可能需要重开游戏后刷新。
