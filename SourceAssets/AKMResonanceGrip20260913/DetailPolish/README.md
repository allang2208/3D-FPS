# AKM 共振二代握把：轮廓与前端精修

2026-09-13，用户要求进一步优化整体线条和前方突出部分。本轮在上次已经补齐后桥的版本上修改，继续使用 AKM 的同一静态配件路径。

## 修改

- 将最前端外伸部分沿枪身方向收回约 8 mm，并在前侧区域平滑衰减至原斜框；前端宽度最多收窄 8%，降低尖头和台阶感。握持主区域、下端与原点不作整体缩放。
- 重做连续上框轮廓：前柱变为倾斜弧面过渡，上梁与前后肩部采用连续圆角，统一小倒角及加权法线；保持后侧支撑闭合。
- 顶部卡边改成更窄的圆角梯形肩面，保持原安装高度与中心。
- 上梁两侧增加浅凹线；前后侧紧固件改为浅沉槽、接近齐平的圆头和真实六角凹孔，减小外凸圆柱。
- 继续使用 AKM 枪钢与原防滑材质，重排改动区域的金属 UV。安装变换、配件 ID 和动画分支未改。
- 为近景细节保留完整精度 UV 和高精度切线数据，并显式重建切线；清除布尔工具带入的多余 UV 层及微小重合碎面。

## 文件与接入

- `refine.py`：本轮作者入口，仅输出本目录的可编辑模型及 FBX。
- `AKM_ResonanceGrip_Polished_Editable.blend`：分件可编辑源。
- `AKM_ResonanceGrip_Polished_Export.blend` / `SM_AKM_angled.fbx`：合并源及游戏导出。
- `import_asset.py`：复用上一级导入器，将本目录 FBX 导入 `/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic/SM_AKM_angled`。
- `Before/` 与 `before-manifest.json`：上轮已接入版本的模型、FBX、uasset 备份。

源材质和原模型的来源许可沿用上一级记录；没有新增外部资产。二进制模型、备份及商业纹理留在本机。

按用户规则，没有执行验收渲染、游戏测试或动画回归。制作/导入记录与用户的视觉验收分开；最终外观由用户测试。

导入入口需要完整编辑器的静态网格编辑子系统：使用 `UnrealEditor-Cmd.exe FPSGAME.uproject /Engine/Maps/Entry -ExecutePythonScript=<本目录/import_asset.py> -unattended -NullRHI -RenderOffscreen`，导入结束自动退出；不要使用不初始化该子系统的 `-run=pythonscript`。此过程只导入和构建资产，不进入游戏或制作渲染。最终保存记录见 `import_receipt.json`，编辑器日志见 `import-editor.log`；不将保存记录称为游戏验收通过。
