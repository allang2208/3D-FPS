# 枪械工作台桌面精修 · 2026-09-28

> 历史版本记录。初版桌面 Authored 已归档；Polish 仍被原台灯恢复及后续小件链引用，保留作制作依赖。当前桌面与发布边界见 [整理发布说明](../../Docs/Publication/workbench-publication-20260928.md)，不要运行旧导入器覆盖其他任务的新桌面。

**已被用户否决并替换。** 本版新做小件不再展示，减面台灯也已移除。当前版本为 `../GunWorkbenchCleared20260928`，只保留桌子、原版台灯和工作垫。下文仅记录历史制作事实，不代表用户认可或当前游戏引用。

已通过后台 Blender 制作与 Unreal Python commandlet 导入、保存；没有启动编辑器界面或游戏，没有进行测试、截图或验收渲染。

## 游戏接入

- 新资产：`/Game/Building/GunWorkbenchPolish20260928/SM_GunWorkbench`
- 已保存到现有建造目录 `DA_VoxelBuildPalette` 的 `gun_workbench_table` 项；保留原 ID、占地、安装方式、枢轴等字段。
- 保存回执：`Receipts/import.json`；后台导入日志：`import.log`。
- 原工作台版本及共享材质仍保留。目录资产修改前备份在 `Receipts/Before`。

## 制作内容

- 保留现有桌体与工作区布局。复用 `SM_WBK_Bench_TaskLamp` 和 `SM_WBK_LampFlex`，保留原 UV，提高曲面保留比例。
- 桌面工具按钢、发黑钢、黄铜、蓝色金属、橡胶、硅胶、尼龙、琥珀色树脂和纸张分别处理。11 个材质使用 21 张贴图；最高 2048，开启正常纹理流送。
- 金属盘使用车削法线及粗糙度变化，去掉原凸起黑色圆环；冲子改为连续滚花；批头座加入凹槽与不同刀头；螺丝刀增加刀口及金属箍；油瓶加入贴合瓶身的标签和细密盖纹。
- 橡胶工具握柄复用项目已有纹理；工作垫另制微颗粒和轻微使用痕迹。共享贴图原文件不修改。
- 新表面图与标签由本地脚本制作；既有 GroundSteel / Grip 来源、材质参数和法线约定记录在 `Authored/surface-materials.json`。

## 可编辑制作源

- `Authored/GunWorkbench_Editable.blend`：独立桌面组件、原台灯和完整材质贴图绑定。
- `Authored/SM_GunWorkbench.fbx`：合并导出，保持原坐标约定。
- `Tools/GunWorkbench/author_polish_surfaces.py`：制作纹理。
- `Tools/GunWorkbench/author_station_polish.py`：制作模型并导出，调用 `bind_polish_surfaces.py` 绑定材质。
- `Tools/GunWorkbench/import_station_polish.py`：导入贴图、材质、模型并更新目录。以首次导入为主，已存在模型时复用已导入模型；更改几何后应使用新的资产版本路径。

本轮完成制作与保存；实际游戏内观感由用户自行测试。
