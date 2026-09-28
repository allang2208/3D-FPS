# 枪械工作台：复用已有弹药盒

2026-09-28，按用户要求增加桌面弹药盒，不重新建模。

## 原件与布局

- 5.56：`/Game/Items/Consumables/ammo_556/SM_ammo_556`，复用两盒。
- 7.62：`/Game/Items/Consumables/ammo_762/SM_ammo_762`，复用一盒。
- 从已安装 UE 静态网格导出，保留原几何、UV、贴图和材质外观；仅等比缩放、旋转、摆放。
- 桌角两盒错落成组，另一盒在侧边工具区。原模型都是开盖包装，不叠放。
- 标签朝向操作区；按盒底放至桌面。5.56 宽 18.5 cm，7.62 宽 21 cm。详细坐标、朝向、比例见 `Authored/manifest.json`。
- 中央工作垫保持空闲；保留桌子、原版台灯、油壶、螺丝刀、钳子、扳手和锤子的位置。

## 交付

可编辑布局：`Authored/GunWorkbench_Editable.blend`。合并导出副本：`Authored/SM_GunWorkbench.fbx`。

更新当前引用的 `/Game/Building/GunWorkbenchLibraryTools20260928/SM_GunWorkbench`，不更换资产地址，不修改建造 ID、占地、交互或存档。已摆放的工作台在下次加载该资产时使用更新外观，无需重新放置。原资产备份位于 `Before/`。

四个弹药材质复制至工作台 Materials 目录，仅增加 Nanite 使用标记；保留原材质图和原纹理引用，不改共享弹药材质。

制作脚本：`Tools/GunWorkbench/prepare_ammo_sources.py`、`place_library_ammo.py`、`import_library_ammo.py`。
资产保存结果记录在 `import.json` 与 `import-commandlet.log`。未启动图形编辑器、游戏、渲染或运行测试，效果由用户测试。
