# 斧头与矿镐写实材质

参考现有 Military Trench 铁铲的灰褐木柄、低饱和旧金属和表面粗糙度，调整正式生产工具的材质。模型、尺寸、挥动、命中时序、采集收益及物品定义保持现状。

## 外观

- 木柄：复用 Normandy 木材的颜色及法线贴图，沿工具长轴铺设木纹，使用灰褐色调和较高粗糙度。
- 金属头：复用 Normandy 金属表面纹理，重映射成深灰旧钢铁，降低原素材大面积橙色锈迹；刃口、尖端及原模型亮色金属部件更亮、粗糙度更低。
- 斧头握柄包裹层：根据原 UV 分区改为深褐色皮革质感，压低高光与凹凸强度。
- 斧头与镐分别使用材质实例，矿镐的木柄略灰、锈蚀比例略高。

原模型是单材质槽、调色板 UV。新的材质按现有 UV 岛区分金属、木柄、包裹层，细节采用工具局部坐标的三向投影，防止挥动或地面翻滚时纹理滑动。保留模型现有法线，再叠加弱细节法线。本次是材质调整，原模型的轮廓与几何块面仍然存在。

## 接入与资源

材质输出位于 `/Game/Items/ProductionTools/Materials`：一个母材质、两个实例、四张共享贴图副本，运行最大尺寸为 2048，启用常规 mip 流式加载。副本来源是 `/Game/UnrealNormandy/Textures/T_WoodSurface_00A_*` 和 `T_MetalRust_00A_*` 的颜色、法线；没有修改 Normandy 源贴图或 EBS 共享母材质。

只改以下现有工具网格的第 0 个材质槽：

- `/Game/EasyBuildingSystem/Meshes/Tools/Polygonal/SM_Polygonal_Hatchet`
- `/Game/EasyBuildingSystem/Meshes/Tools/Polygonal/SM_Polygonal_Pickaxe`

手持和地面掉落均读取这两个网格，原物品存档继续使用相同路径，无需重新领取工具。材质及贴图随已配置烘焙的工具网格硬引用进入打包。背包中的静态 PNG 图标本次未重制。

可编辑材质生成入口：[apply_tool_materials.py](../Tools/Production/apply_tool_materials.py)，着色器源码：[ProductionToolSurface.hlsl](../Tools/Production/ProductionToolSurface.hlsl)。在当前 UE 工程中运行：

```powershell
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
  'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript `
  '-script=D:/FPS3D/FPSGAME/Tools/Production/apply_tool_materials.py' `
  -unattended -nop4 -nosplash -AllowCommandletRendering
```

原网格与本次已存在资源的备份、散列、制作输入及安装记录保存在本机 `SourceAssets/ProductionToolMaterials20260913/`。授权素材及派生 uasset 留在本机，公开仓库仅发布制作脚本和说明。

## 交付范围

制作脚本已保存上述 9 个资源，安装回执为本机 `SourceAssets/ProductionToolMaterials20260913/material-install.json`。命令行进程因工程已有的 `GameFeatureData` 配置报错及另一个编辑器占用 8000 端口而返回 1；脚本完成资源保存并输出 `PRODUCTION_TOOL_MATERIALS_INSTALLED`，没有将该返回码记为构建或验收通过。日志位于 `Saved/ProductionToolMaterials/apply-materials-final.log`。

仅执行制作、必要材质构建和资源保存；未进行 PIE、截图、渲染预览或运行验收，由用户在游戏中测试。当前已打开的编辑器可能仍持有旧网格或材质，保存自己的场景后重新打开工程，再装备 6 / 7 查看。
