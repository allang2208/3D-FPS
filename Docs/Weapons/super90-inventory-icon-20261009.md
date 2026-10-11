# Super90 装备栏贴图修复（2026-10-09）

用户反馈装备栏贴图不合格，本次定位并替换正式图标，未运行游戏测试。

## 原因

`ColdSteelInventoryWidget::LoadIcons` 给 Super90 请求动态图，同时读取 `Content/ColdSteelData/Icons/ue_super90.png` 作为等待或失败时的回退图；`ItemBrush` 在动态图就绪后优先使用动态图。

旧 PNG 本身为紫红色缺材质图，512×512、枪口朝右。它来自早期 Blender 脚本，未使用当前已保存的 WS1 枪械材质，方形取景也与 4×2 占格和横向装备图区不一致。问题已写进像素，并非装备栏染色参数造成。

## 修复

- 使用现有 `ColdSteelWeaponIconCatalog` commandlet，仅导出 `ue_super90`；直接复用动态图的模型、材质、可见分件、正交取景和透明背景。
- 正式 PNG 已落盘：640×320，枪口朝左，按可见轮廓居中，主轴填充 91%。当前模型为 `/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7`。
- 旧制作脚本 `SourceAssets/BenelliM4Super9020261006/render_catalog_icons.py` 的枪械导出改为调用现有 UE 目录图制作工具；不再用旧 Blend 覆盖枪械图标。其余装备和弹药导出范围保留。
- 图标路径沿用既有定义，新旧存档都会读取同一路径；运行时动态图仍按实例配件生成。

复现制作命令：

```powershell
& Tools/UI/build_weapon_catalog_icons.ps1 -Definitions ue_super90
```

本次后台导出日志为 `SourceAssets/Super90InventoryIcon20261009/export.log`：`WeaponIconCatalog: wrote .../ue_super90.png`、`COMPLETE failures=0`，进程退出 0。旧图保存在同目录 `Before/ue_super90.png`。

此图以 PNG 直接加载，替换不需要 UTexture 导入或原生代码编译。未改面板布局、模型或换弹动作；未启动编辑器界面、PIE 或游戏。装备栏实机效果仍由用户测试。
