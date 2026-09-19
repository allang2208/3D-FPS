# 镂空轻型枪托：用户指定 Meshy 资产

源包：`D:/FPS3D/资产/Meshy_AI_Rifle_Stock_0914005605_image-to-3d-texture_fbx.zip`。用户随后将显示名调整为“镂空轻型枪托”：取消 ADS 瞄准时间减益、后坐力控制提高 10%、枪械稳定性增加 5%。数据为 `recoil_mult=0.9`、`stability_mult=1.05`，删除此配件的 `ads_percent` 修正。M4、AKM、QBZ191 同步使用新数值，内部 ID `core_stock` 与 Meshy 模型保持不变。原骨架枪托 `skeleton` 与高性能后托 `qr_performance` 保持独立。

## 制作

- 原始 FBX 与四张贴图保存在 `Source/`，原模为 1,945,222 三角面。`Imported_Source.blend` 保留原始导入状态；来源散列见 `provenance.json`。原包和派生二进制留本地，未作公开再分发。
- 游戏主体减至 80,000 三角面，保留源 UV0；将高模几何与原结构法线烘焙到 4K `Textures/Normal_Game.png`。原色图为 4K，金属度和粗糙度为 2K，均保留源文件。
- 沿用核心枪托主体 20 cm 长度。安装轴由新源上方圆管前端确定，源坐标约 `(-0.951789, 0.0004, 0.488)`；不使用整个枪托高度的中心。
- M4、AKM 沿用各自现有 StockMount，连接环按新模型管口制作。AKM 保留带通孔机匣盖，QBZ191 保留独立肩台并将网格预变换到它的 WPN_root 空间。
- 源金属度图作为材质遮罩：金属区域分别匹配 M4、AKM、QBZ191 的现用涂层，非金属区域保留 Meshy 颜色和粗糙度，肩垫保留橡胶身份。UV1 承载机匣涂层，新连接件不采样主体结构法线。UE 导入脚本中的材质为最终版本，Blender 金属显示使用源工作材质。
- 含连接件的导出面数：M4 81,536；AKM 82,752；QBZ191 81,912。导出数值见 `variant_authoring.json`，不代表游戏性能已测试。

## 文件与运行引用

`prepare_source.py` 加载来源，`mount_coordinates.py` 读取源管口截面用于制作；`author_low.py` 减面和法线烘焙；`author_variants.py` 导出逐枪模型；`import_assets.py` 导入资源及最终材质。

- `CoreStock_Bake_Editable.blend`：烘焙作者场景。
- `CoreStock_Low_Editable.blend`：游戏主体与隐藏的源高模。
- `{M4,AKM,QBZ191}/CoreStock_Game_Editable.blend`：各枪可编辑场景。
- `{M4,AKM,QBZ191}/SM_CoreStock.fbx`：各枪 UE 导入文件。
- `Before/`：本轮修改前的源码和交付状态快照。

新资源目录为 `/Game/Weapons/CoreStock20260914/Meshy0914005605/{M4,AKM,QBZ191}/SM_CoreStock`，已有 CoreStock20260914 打包目录覆盖此子目录。`SkeletonStockVisual.cpp` 与 `QBZ191Attachments.h` 精确切换核心枪托路径，共用角色、改造预览、图标与掉落装配入口。旧 5080 版本和原骨架枪托资产保留。

## 接入状态

三枪资源已导入并保存，导入进程退出 0，日志为 0 error(s)、0 warning(s)，回执见 `import_results.json`。首次导入的 Clamp 属性写法已修正，并完成重新导入；AKM 连接件已在导出前完成三角化。

用户保存并关闭编辑器后，已执行 `Tools/Build/Build-Editor.ps1`，完整依赖构建结果为 `Succeeded`，退出 0；UBT 报告目标已是最新状态（`Target is up to date`）。记录见 `build_editor.log`，引擎日志为 `Saved/BuildEditor/build-20260914-091319.log`。用户重新打开项目后加载本轮核心枪托引用；未启动游戏验证。

依照用户规则，本轮未启动游戏、未生成预览或验收渲染、未运行测试，外观、装配和性能交由用户测试。
