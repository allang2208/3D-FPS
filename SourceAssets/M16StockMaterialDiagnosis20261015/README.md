# M16 伸缩后托：原始低模与法线配对恢复（2026-10-15）

用户看到旧源白模平整，要求继续排查贴图与模型的区别。本轮获授权进行同网格、同相机、同灯光的材质对照；未启动 UE 编辑器或游戏。

## 定位结果

- `Preview/A_constant_no_texture.png`：前一轮移植的旧 M16 游戏网格，常量金属材质，无贴图。没有菱形斑块，但可见局部反光起伏。
- `Preview/B_R2_structural_normal.png`：同一网格、光照、相机及材质参数，只加入 R2 法线。出现与用户截图对应的大片菱形反光斑块。R2 原 PNG 本身包含这些异常图案。
- `Preview/C_original_bake_normal.png`：同一已修整网格配原始法线，菱形消失，但旧低模修整后的形状/法线已不再是原烘焙目标，仍有不匹配的起伏。
- `Preview/E_old_mesh_recalculated_normals.png`：仅重算同一网格法线不能解决问题。
- `Preview/G_original_low_matched_normal.png` 与 `H_original_high_constant.png`：恢复 20260914 原始低模及其匹配法线后，反光与原高模接近。没有继续全局平滑、削弱法线或重新生成造型。

这些对照确认 R2 法线纹理引入了主要的菱形异常，并支持将原始低模和原始法线作为完整配对恢复。没有把全部残余细微起伏归因于贴图，也没有声称还原出原生成模型缺失的结构。

## 制作及接入

- 从 `StockRefresh20260914/TacticalTelescopic/M4/TacticalStock_Game_Editable.blend` 恢复原始低模、UV 和角点法线，按既有刚体变换适配 M16。
- 保留 `M16StockDonor20261015/Final` 中 M16 的 1,268 个安装接口三角形、UV 和角点法线。
- 原始 4K `Normal_Game.png` 完整复制为 M16 私有纹理，强度为 1。UE 使用 Normalmap 压缩、关闭 sRGB、仅导入时转换一次绿色通道。
- 复制旧金属/聚合物材质实例及其父图，替换结构法线采样；橡胶材质亦为私有副本。颜色、粗糙度、金属分区和原湿润逻辑保留。M16 湿润表增量加入私有材质自映射。
- 只替换 M16 `tactical_telescopic` 的原运行路径，更新它在 `current_surface_bindings.json` 中的绑定。没有修改共享法线纹理、M4 或其他枪的后托。
- 前一版新建硬表面模型保留在独立源资产路径，M16 当前已改回本轮原款模型。

运行网格：`/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_tactical_telescopic`。

私有模型、材质和法线：`/Game/Weapons/M16A2/TelescopicMatchedSurface20261015/`。

## 落盘与对照边界

后台 Python commandlet 完成并退出 0，`install_receipt.json` 的 `complete=true`。导入日志 0 错误、6 条 FBX 内嵌纹理重名提示；材质/纹理自动导入已关闭，实际材质与纹理由脚本显式绑定。未出现近零切线提示。

`Final/SM_M16_Telescopic_SavedUE.fbx` 来自保存后的实际 UE 网格。`Preview/I_repaired_saved_mesh.png` 使用这份导出及匹配法线，在与诊断相同的灯光、相机和常量金属参数下渲染，菱形异常已消失。该图用于隔离表面问题，**是 Blender 诊断图，不是 UE 游戏画面，也不是实际配色预览**。

作者网格 82,804 三角形；UE 构建后导出 82,687 三角形。没有另增细分、重网格或手工变形，导入沿用退化面移除。

本轮完成范围为模型/法线配对恢复、私有材质、资产构建保存和用户授权的离线对照。未做游戏、多人或天气运行测试，最终游戏观感由用户确认。

入口：`render_ab.py` → `compare_source.py` → `restore_matched_source.py` → `install_matched.py` → `render_saved.py`。

## 2026-10-16 整理记录

本目录已确认退役的备份、候选或一次性操作已移至本机 `trash/weapon-attachments-retired-20261016/SourceAssets/M16StockMaterialDiagnosis20261015`。原文的 Before/旧候选路径属于历史记录；当前恢复依赖已保留。准确清单、替代物及本轮发布边界见 [整理发布说明](../../Docs/Publication/WeaponAttachments20261016/README.md)。
