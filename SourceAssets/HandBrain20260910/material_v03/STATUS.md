# 手脑材质 V03

2026-09-11。绿色材质与细节第一轮；Fab 素材领取完成，文件下载及接入尚未完成。

- 来源：原混元贴图 + 本地 Blender 材质节点。没有将商店预览图作为纹理，也没有使用尚未下载的 Fab 素材。
- 调整：深橄榄绿皮肤，局部斑驳与微表面法线，皮肤/伤口粗糙度分离，暗红湿润口腔与老化牙齿。当前主要改善表面表现，未重雕手指或补全关节几何。
- 15 张有效 UV 烘焙贴图：主体 4K，其他区域 2K。原口腔 UV 退化，3 张口腔测试烘焙无效，不供引擎使用；口腔使用独立可调颜色和粗糙度材质。
- 可编辑节点源：HandBrain_Refined.blend；重新加载烘焙贴图的源：HandBrain_Refined_Baked.blend。Before.png / After.png 是同灯光同机位比较；Baked_check.png 是重建烘焙材质后的渲染。
- 几何顶点检查保持一致，38 骨、五动作及其时长保持一致；本轮不修改玩法 C++。
- UE：/Game/Monsters/HandBrain/RefinedV03；SK_HandBrain 的六个材质槽切换为新材质，旧材质资源保留。ue_import_report.json 记录本次导入槽位；原始槽位是 /Game/Monsters/HandBrain/Materials/M_HandBrain_0 至 5。
- 村庄强橙色灯光会压掉绿色差异，不能仅凭远景认定细节已达到最终质量；中性光细节图是 Blender 渲染，不冒充 UE 截图。

## Fab 资源与接续

已在用户账户领取 **Organic Surface Material**，作者 **Stone Material**。

- 商品：https://www.fab.com/listings/e41a57c0-4685-48cf-bed4-d77be4963b5a
- 页面许可：CC BY 4.0，https://creativecommons.org/licenses/by/4.0/
- 4K Base Color / Normal / Roughness / AO / Height，支持 UE 5.3–5.8。
- 网页库已显示领取成功；下载弹窗明确 UE 文件需要 Epic Games Launcher 或 Fab UE5 插件，网页没有文件下载链接。当前工具不能操作原生应用，该阶段待用户添加到项目。
- 收到文件后记录本地路径/散列，查看实际纹理，按伤口/皮肤遮罩与现有绿皮混合，再渲染验证；保留作者、商品链接、许可和修改说明。当前 V03 不属于 Fab 材质渲染结果。

## 重建入口

工具目录 D:/FPS3D/FPSGAME/Tools/HandBrain/：

1. refine_materials.py：节点材质与中性光预览。
2. bake_refined_materials.py：在静止绑定姿态烘焙，微表面随皮肤 UV 变形。
3. verify_refined_bake.py：检查有效烘焙并重建材质渲染，排除无效口腔贴图。
4. import_refined_materials.py：导入新材质，不重新导入骨架、动画或 Physics Asset。
5. Open-HandBrainVillage.ps1 -Audit：隔离存档实机验收。

运行日志在 Saved/HandBrain/material-*.log，行为结果以本次运行生成的 acceptance.json 为准。命令行导入仍有项目既有 GameFeatureData 配置和端口占用错误；材质专用完成标记独立检查，不把全工程日志称为无错误。
