# 冶炼面板（2026-09-23）——锭类占位图标

对应规划与实现记录：`Docs/UI/smelting-panel-plan-20260923.md`（第 7 节）。
玩法/存档代码在 `Source/`（`Building/SmeltingSystem.*`、`UI/ColdSteelSmeltingWidget.*`、
`UI/ColdSteelSmeltingHUD.cpp`），本目录只放图标生成脚本与回执。

- `make_ingot_icons.py`：系统 python + numpy/PIL，生成 4 张 256×256 透明底占位图标到
  `Content/ColdSteelData/Icons/{iron,copper,silver,gold}Ingot.png`。风格对齐冷钢图标约定
  （左上柔光、无烘焙文字/数量/状态）；正视铸锭＝梯形顶面＋收分前立面＋落地软影。
- `ingot-icons.json`：逐张来源回执（source=generated）。规划文档第 1 节明确锭的**正式渲染图**
  属后续 `ue5-item-asset-workflow` 范围，本套只是占位。

重跑：

```powershell
python SourceAssets/SmeltingPanel20260923/make_ingot_icons.py
```

PNG 按仓库既定忽略规则只保留本机；`items.json` 的 `ue_icon` 字段运行时按
`Content/ColdSteelData/` 相对路径直接读文件（`FImageUtils::ImportFileAsTexture2D`），
不需要 .uasset。
