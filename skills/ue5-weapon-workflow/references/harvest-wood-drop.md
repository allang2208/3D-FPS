# 木材掉落：短原木、1×2 与图标

2026-09-24。砍树得到的木材与地面短原木共用同一根圆柱，背包占 1×2。体素木块图标仍是立方体 `Icons/wood.png`，不要改成这张图。

- 运行时掉落网格只使用 `/Game/Items/HarvestTimber/SM_PoplarLog_Solid_A`。不要再按 A/B/C 轮换短木；树桩和倒木保持原样。
- `BaseFootprint` 在枪械格子之前对 `wood` 返回 `FIntPoint(1, 2)`。读档时把旧的 1×1 宽高和 `ue_icon` 迁到目录值，否则旧档继续画立方体、占一格。
- 图标文件是 `Content/ColdSteelData/Icons/wood_log.png`，`items.json` 的 `wood.ue_icon` 指向它。运行时用 `FImageUtils::ImportFileAsTexture2D` 从 `Content/ColdSteelData/` 读取物品实例上的路径。改这张 PNG 不要在内容浏览器里重新导入成 uasset。
- 取景对齐枪械图标：剪影居中，长轴约占画布 91%。1×2 格子用竖幅（本次 512×1024），原木长度沿画面高度。
- 不要用编辑器 SceneCapture2D 或导出渲染目标当交付。那条路没有可靠落盘，横躺时还会把长度填进宽度。交付路径是 `Tools/HarvestTimber/export_wood_log_obj.py` 导出 OBJ，再由 `render_wood_log_icon.py` 用网格和 `T_PoplarSolid_BaseColor.png` 离线栅格化。OBJ 留在 `Saved/HarvestTimber/`，不进 Git。
- C++ 改完后，编辑器里的模块要等本次构建成功并且重新进游戏读档才生效。只重启、仍加载旧 DLL 时，木材会继续是旧图标和 1×1。
