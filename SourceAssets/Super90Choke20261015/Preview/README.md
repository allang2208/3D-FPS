# SUPER90 收束器装配预览

用户于 2026-10-15 要求查看衔接和整体效果。本目录是 Blender 装配渲染，不是 UE 游戏截图。

`export_current.py` 只读导出当前已保存的 `SK_Super90_V7` 与 `SM_ShotgunChoke_Box01`，并记录材质参数与贴图。`render_preview.py` 使用 `M4MuzzleVisual.cpp` 的安装坐标组装，保留原厂枪托、握把与机瞄；隐藏第一人称皮肤和仅换弹时显示的临时散弹，保留枪身侧面的备用弹。

- `super90_choke_overall.png`：整体比例。
- `super90_choke_connection.png`：上方枪管、连接座、下方弹仓和收束器近景。
- `Super90_Choke_AssemblyPreview.blend`：可编辑预览场景。
- `capture.json`：实际导出来源及材质。
- `preview_receipt.json`：安装矩阵、输出与渲染来源。

使用中性棚拍光；Blender 按 WS1 基色、粗糙度及结构法线近似表达材质，不包含 UE 场景光照与天气效果。预览导出中的重复材质名后缀已重新绑定。未修改游戏资产、数值或安装坐标，未运行游戏或联机测试。
