# 免费写实斧头接入（2026-09-13）

用户本轮最终指定先做斧头。正式物品 `tool_axe` 改用 VEE ANIMATION 的 [Axe Game Ready 3D Asset](https://www.fab.com/listings/cd5e9124-55b7-4021-8544-a4dc9a7ca0d7)。矿镐和铁铲保留当前资产。

## 来源与资源

- 用户下载的 FBX：`D:/FPS3D/VaultCache/FabLibrary/Axe_Game_Ready_3D_Asset-cd5e9124/fbx/axe_fbx_extracted/Axe.fbx`。
- 用户提供的纹理包：`D:/FPS3D/资产/axe_textures.zip`。
- Fab 页面标注 Standard License；原包、派生二进制资源留在本机，不公开再分发独立模型或贴图。
- 本机母版、输入备份和回执：`SourceAssets/FreeProductionTools20260913/`。
- 正式网格：`/Game/Items/ProductionTools/FreeFab20260913/Axe/SM_Free_Axe`。
- 六个 UE 资源：一个网格、一个材质和四张 1024×1024 贴图（BaseColor、Normal、Roughness、AO）。

## 制作与接入

源网格 868 个顶点、1728 个三角面。按现有生产工具的 Z 轴朝上、居中枢轴适配为 78 厘米长，配置缩放为 1。保留 UV、轮廓和原有表面细节；材质使用原包纹理。源 FBX 指向作者电脑上的贴图路径，因此重新绑定本机纹理。

实际 ZIP 不包含网页描述中的 Metalness。按独立几何连通块识别斧头、木柄、金属楔，使用顶点颜色 R 保存钢铁遮罩，维持单材质槽。材质中钢铁金属度为 0.9，木柄为 0，棕色氧化处降低金属度。Height 原图保留作源文件，不增加实时位移。启用纹理常规 mip 流送，网格不启用 Nanite。

`production_tools.json` 切换斧头路径和缩放；打包目录加入该资源文件夹。旧斧头网格及上轮材质保留，便于后续恢复。

旧存档实例自身保存了工具参数，因此在载入及提交数据时，仅同步斧头的模型路径、缩放和三个持握旋转字段。物品 ID、数量、背包/仓库/掉落位置、采集收益、挥动和接触时序保持原样。手持与掉落仍使用现有异步资源加载。背包 PNG 图标暂时沿用原图。

制作入口：

- `Tools/Production/read_free_tool_source.py`：读取源模型结构，供尺寸、材质适配使用，不渲染。
- `Tools/Production/prepare_free_tool_models.py`：Blender 中制作钢铁遮罩、尺寸和枢轴，导出 FBX。
- `Tools/Production/import_free_axe.py`：UE Python 导入模型、构建材质并保存资源。

## 当前交付状态

六个资源已保存，回执为 `SourceAssets/FreeProductionTools20260913/axe-import.json`。导入脚本执行完成。命令进程因工程既有的 GameFeatureData 配置和 8000 端口占用错误返回 1；没有把该返回码记为整工程成功。日志：`Saved/FreeProductionTools/import-axe.log`。

用户关闭编辑器后，已通过 `Tools/Build/Build-Editor.ps1` 完成普通 Editor 构建（`Result: Succeeded`），日志为 `Saved/BuildEditor/build-20260913-211636.log`；使用 `-NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles` 生成普通模块。运行测试及效果判断由用户进行；本轮没有启动 PIE、生成截图或渲染验收。

完成构建并重新打开工程后，按 `6` 装备伐木斧查看，`F7` 收起。旧存档中的斧头无需丢弃或重新领取。
