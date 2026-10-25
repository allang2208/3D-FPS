# 符文战锤外观修订 · 2026-10-24

范围：迅捷／破坏魔力符文的独立纹样、锤柄位置和标准图标；终律·镇魂钟的实体拱窗、贴合纹饰与锤面细节。

采用既有参考图，保留安装接口、玩法和动画。图标由内置 imagegen 根据项目金属框母版生成；制作与导入回执单独保存。未运行游戏、测试或验收。

已完成独立后台作者工程保存并按共享批次互斥接入主工程，共 12 项新资产：镇魂钟网格、三张 PBR 贴图、三份材质、两张符文遮罩、三张 UI Texture2D。正式 PNG 与两份运行配方已更新；旧版来源保留。

- `author_masks.py`：新矢量纹样与贴图。
- `prepare_sources.py` / `bell_geometry.py`：V2 几何，源和导出在同级 `FinalTollHammerHeadV2`。
- `imagegen_prompts.json` / `Icons`：内置图像工具提示词和最终母图。
- `author_isolated.py` → `install_packages.ps1`：后台保存新包，再以共享互斥安装并发布。
- `import_receipt.json` / `publication_receipt.json`：实际保存、安装与引用回执。
- `build_receipt.json`：Editor 成功；Game exit 6，受其他多人存档代码的 `ServerSubmitProfileChunk` 八参数声明与六参数调用／实现不一致阻挡。本次未修改该并行文件。

活动图标由现有 UI 读取 `Content/ColdSteelData/AttachmentIcons20260913` 中的 PNG；对应新版 Texture2D 保存在 `/Game/Weapons/RuneboundWarhammer20261022/RuneIconsV3`，旧根目录 Texture2D 仅保留为非活动来源。
