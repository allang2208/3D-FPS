# HK416 装备栏与背包图标

2026-10-01，按用户要求更新装备栏与背包共用的 HK416 图。

- 使用现有 `ColdSteelWeaponIconCatalog -Definition=ue_hk416` 后台出图，读取当前 UE 模型、原厂装配和游戏材质，不再使用旧 Blender 方形图片。
- 输出 800×320 透明横图；装备栏、背包和物品提示沿用现有目录图引用，动态改造图继续由原有配方缓存生成。
- 已替换 `Content/ColdSteelData/Icons/ue_hk416.png`，导入并保存 `/Game/ColdSteelData/Icons/ue_hk416`，设置 UI 纹理组、sRGB、图标压缩和无 mipmap。
- 原 HK416 图标作者入口改为复用新的 UE 装备图，原配件图标制作流程保留。模型或材质以后变化时，先执行本批 `export_icon.ps1` 再发布。

制作入口与回执：`SourceAssets/HK416InventoryIcon20261001/export_icon.ps1`、`import_icon.py`、`import_receipt.json`。旧 PNG 在该目录内保留为 `ue_hk416_previous.png`。

离线出图进程使用 `-NoTextureStreaming` 取得目录图所需贴图；没有修改游戏的流送设置、运行时异步队列或重试预算。PNG 导出不保存 UE 内容包；纹理导入通过现有编辑器的批次互斥桥完成，只保存本张图标。

已完成制作与导入保存，未运行游戏或追加验收；用户重新进入游戏后查看装备栏和背包效果。
