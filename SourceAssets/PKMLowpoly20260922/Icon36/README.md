# PKM 背包图标修复（Icon36）

2026-09-23。用户反馈「PKM 在背包栏中无法获取贴图」。本轮只补目录图标和物品定义字段，不动模型、材质、动作，也不改 Motion21 之后的提把参数。

## 现象与根因

- 背包、装备栏、仓库与浮窗按同一顺序取图：动态图标就绪用实时图，等待或失败时用 `Content/ColdSteelData/Icons/<definition>.png`（`ColdSteelInventoryWidget::LoadIcons` / `ItemBrush`，浮窗见 `ColdSteelItemTooltip::RefreshIcon`）。
- `ue_pkm_lowpoly` 已在 `UColdSteelWeaponIcons::Supports()` 名单里，所以取图走 `Icons/ue_pkm_lowpoly.png`，而该文件**从未生成**：`ColdSteelWeaponIconCatalogCommandlet` 的默认定义列表里没有 PKM。
- 实测日志（`Saved/Logs/FPSGAME.log`，2026-09-23 13:22）显示 PKM 的动态图标渲染失败后按设计回退目录图，但目录图不存在：

  ```
  WeaponIcon: prepare key=ue_pkm_lowpoly|barrel=short|bipod=pkm_bipod|... mesh=/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular.SK_PKM_Manny_Modular
  WeaponIcon: render failed ue_pkm_lowpoly|...; using catalog image
  ```

  同一段日志里 M4／AKM／SVD 等也回退，但它们有目录 PNG；只有 PKM 落到「既没有实时图、也没有目录图」，格子退回只画物品名（`ColdSteelInventoryPresentation.cpp` 的无画刷分支）。
- `items.json` 的 `ue_pkm_lowpoly` 当时是 `"icon": ""` 且没有 `ue_icon`，按定义取图的其它界面同样没有兜底。

## 改动

1. `Content/ColdSteelData/Icons/ue_pkm_lowpoly.png`：用共享目录图标 commandlet（与背包同一套装配、材质、灯光、透明背景和取景）渲染，768×320 RGBA，52,546 字节。
2. `Content/ColdSteelData/items.json`：`icon` 与 `ue_icon` 同指 `Icons/ue_pkm_lowpoly.png`，保留 `icon_fallback: "PKM"`。
3. `Source/FPSGAME/UI/ColdSteelWeaponIconCatalogCommandlet.cpp`：默认定义列表补入 `ue_pkm_lowpoly`，整批导出不再漏这一件。

## 结果与边界

- 命令入口 `Icon36/build_catalog_icon.ps1`：`-run=ColdSteelWeaponIconCatalog -Definition=ue_pkm_lowpoly -AllowCommandletRendering -NoTextureStreaming -RenderOffscreen`，并对该进程关闭 MCP 自动启动。`catalog-export.log`：`WeaponIconCatalog: wrote D:/FPS3D/FPSGAME/Content/ColdSteelData/Icons/ue_pkm_lowpoly.png`、`COMPLETE failures=0`、`Success - 0 error(s)`，退出码 0。
- 图像量化核对：RGBA、四边完全透明、有效像素 34,837（alpha > 10）、内容包围盒 (35,78)–(732,241)，没有裁切；整枪、弹箱、木托与提把都在画面内。
- 常规 Editor 目标构建成功（`build_editor.log`，`Saved/BuildEditor/build-20260923-213307.log`），退出码 0，未启动编辑器。
- 未运行游戏、未跑验收脚本；背包／装备栏／仓库／浮窗的实际显示由用户实测。

## 同类发现（本轮未处理）

`ue_dan_wesson715` 也在 `Supports()` 名单里，但 `Content/ColdSteelData/Icons/ue_dan_wesson715.png` 不存在——该枪 2026-09-13 的记录写明「本次未执行目录图标渲染」，所以动态图标失败时它同样会退化成只有名字。本轮按用户指定的 PKM 范围处理，没有顺带渲染这一件。
