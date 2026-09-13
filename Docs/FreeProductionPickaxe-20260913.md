# 免费写实十字镐接入（2026-09-13）

用户已下载并授权接入 REAL DEDICATED 的 [Basic Pickaxe](https://www.fab.com/listings/46ea08b2-1947-40f8-b1e7-f1254d49a912)，用于正式物品 `tool_pickaxe` 的手持与掉落外观。

## 来源与制作

- 用户下载目录：`D:/FPS3D/VaultCache/FabLibrary/Basic_Pickaxe-46ea08b2/fbx/basicpickaxe_fbx_extracted/`。
- Fab Standard License。原始 FBX/TGA、Blender 母版和 UE 二进制只保留在本机；源码仓库发布制作脚本和接入配置。
- 本机输入备份：`SourceAssets/FreeProductionTools20260913/Original/Pickaxe/`，沿用已有忽略规则。
- 编辑母版：`SourceAssets/FreeProductionTools20260913/Pickaxe-fitted.blend`。三个 LOD 分别导出到同目录的 `UE/Pickaxe_LOD0.fbx`、`Pickaxe_LOD1.fbx`、`Pickaxe_LOD2.fbx`。
- 正式网格：`/Game/Items/ProductionTools/FreeFab20260913/Pickaxe/SM_Free_Pickaxe`。

源 FBX 内含三个重叠的 LOD 对象，不能合并为一个模型。使用 LOD0 的包围范围计算统一变换，三档均按原比例适配为 70 厘米长、约 62 厘米头宽、5.3 厘米厚，Z 轴朝上、中心枢轴。保留 UV、原作者轮廓和材质分区。

保留原作者 LOD：510 / 374 / 190 个三角面，屏幕尺寸阈值为 1.0 / 0.15 / 0.05。使用普通静态网格、单材质和简单碰撞；不启用 Nanite。

材质直接绑定五张原始 512×1024 TGA：BaseColor、Normal、Metallic、Roughness、Occlusion。颜色图开启 sRGB，法线使用法线压缩，其余使用线性遮罩压缩；启用常规 mip 纹理流送。不放大源贴图，不额外增加实时位移。

制作入口：

```powershell
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python 'D:/FPS3D/FPSGAME/Tools/Production/prepare_free_pickaxe.py' -- 'D:/FPS3D/VaultCache/FabLibrary/Basic_Pickaxe-46ea08b2/fbx/basicpickaxe_fbx_extracted' 0.70
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript '-script=D:/FPS3D/FPSGAME/Tools/Production/import_free_pickaxe.py' -unattended -nop4 -nosplash -AllowCommandletRendering '-abslog=D:/FPS3D/FPSGAME/Saved/FreeProductionTools/import-pickaxe.log'
```

## 游戏接入

`production_tools.json` 更新矿镐的模型路径与缩放（1.0），`DefaultGame.ini` 添加对应打包目录。手持与地面掉落沿用现有异步加载、碰撞和质量设置。

旧存档已保存工具模型路径，因此在现有载入/提交归一化中，将外观同步范围由斧头扩展到矿镐，仅更新模型、缩放和持握旋转字段。物品身份、数量、背包/仓库/掉落位置、采矿产出、0.68 秒挥动和 0.24 秒接触时序保持原样。斧头和铁铲配置、背包图标不在本次替换范围内。

## 交付状态

七个 UE 资源已保存，回执为 `SourceAssets/FreeProductionTools20260913/pickaxe-import.json`。导入脚本已执行完成，日志为 `Saved/FreeProductionTools/import-pickaxe-final.log`。命令进程因工程既有的 GameFeatureData 配置缺失返回 1，不能把该返回码记为整工程成功。

用户保存并关闭编辑器后，已通过 `Tools/Build/Build-Editor.ps1` 完成普通 Editor 构建调用，结果为 `Succeeded`、`Target is up to date`，无需额外编译动作。日志为 `Saved/BuildEditor/build-20260913-215511.log`；使用普通模块构建参数，不使用热重载 DLL 后缀。按用户规则未主动运行游戏测试、PIE、截图或渲染验收。

重新打开工程后按 `7` 装备矿镐，左键采矿，`F7` 收起。旧存档的矿镐会使用新外观，无需重新领取。初版尺寸、持握构图和最终材质观感由用户进游戏判断。
