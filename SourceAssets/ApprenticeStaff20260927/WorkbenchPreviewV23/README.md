# 长杖改造预览水晶修复 V23

## 原因

原厂杖头网格 `SM_Staff_head_crystal_false` 已包含水晶，部件表、异步加载和预览 ShowOnly 列表均包含该杖头。当前网格使用 V22 薄透明水晶材质。

工作台采用 FinalToneCurveHDR 颜色捕获与 SceneColorHDR 反向覆盖率捕获，UI 透明度来自 `1 - PreviewCoverage.A`。UE 5.8 的 Thin Translucent 双源混合保留目标 alpha；清屏 alpha 为 1 时，孤立的水晶区域会被 UI 合成为全透明。提高世界材质 Opacity 不能修复这条覆盖率链路。

本地引擎依据：`Engine/Source/Runtime/Renderer/Private/TranslucentRendering.cpp` 的 Thin Translucent blend state、`Engine/Shaders/Private/BasePassPixelShader.usf` 的双源输出，以及 `MaterialShared.cpp::FMaterialResource::IsDualBlendingEnabled`。双源开关由材质模型和平台决定，没有可独立关闭的材质属性。

## 改动

- `M4StaffGunsmith.cpp` 将预览水晶材质加入同批异步加载，在临时展示组件上仅替换 V22 原厂水晶材质槽。切换改造件继续使用已有完整装配重建，不修改武器网格的默认材质。
- 新资产 `/Game/UI/GunsmithWorkbench/M_StaffQuartzPreviewV23` 使用 Default Lit / Translucent / Before DOF，正确写入反向覆盖率。保留 V22 的本地空间云雾、不透明度 0.84–0.96、粗糙度 0.18–0.27 与颜色，使用灰度透明近似以适配 UI 合成。
- 水晶几何、杖头安装点、上端绳索、游戏内 Thin Translucent 材质和共享预览灯光保持原状。
- 新材质在现有工作台 cook 目录内。没有 Tick 同步加载、额外捕获或项目全局透明度配置改动。

## 恢复和制作

先执行 `install_preview_material.py`，再构建 FPSGAMEEditor。脚本复用 `../QuartzAimV22/ue_quartz_material.py` 的预览分支；默认分支仍输出原来的世界材质。修改前源码位于 `Before/`。

已有 UE 编辑器且退出 PIE 时，通过 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript` 执行；编辑器关闭时用无界面 `-run=pythonscript -nullrhi -script=<absolute script path>`。不要在 PIE 保存资产，不要同时启动另一进程覆盖编辑器持有的资产。

## 当前交付证据

用户关闭 UE 后，后台 commandlet 已创建并保存预览材质；`install-receipt.json` 记录了实际世界网格材质槽、预览着色模型和 Before DOF 设置，`complete=true`。首次 PIE 保存失败保留在 `install-bridge01.txt`，后续实际保存见 `install-commandlet.log`。

FPSGAMEEditor Win64 Development 基础 DLL 已成功编译：`Saved/BuildEditor/build-20260927-232835.log`，4 个构建动作，包含 `M4StaffGunsmith.cpp` 和 `UnrealEditor-FPSGAME.dll`。产物记录见 `build-receipt.json`。未主动打开或重启编辑器。

本次只排查指定缺失水晶问题；未启动游戏、渲染预览或进行全武器验收。实际改造栏画面交由用户确认。
