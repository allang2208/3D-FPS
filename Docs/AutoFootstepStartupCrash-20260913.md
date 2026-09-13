# AutoFootstep 启动崩溃修复（2026-09-13）

## 原因

本轮采集效果的 Editor 构建使用了 `-ModuleWithSuffix=FPSGAME,913972`，沿用了已有热重载状态。该构建成功并不代表生成的模块引用一致：

- 插件模块清单指向 `UnrealEditor-AutoFootstep-0071.dll`。
- `UnrealEditor-AutoFootstepEditor-0071.dll` 引用插件的 `0071` 版本。
- 游戏模块 `UnrealEditor-FPSGAME-913972.dll` 的 PE 导入表仍引用 `UnrealEditor-AutoFootstep-91614.dll`。
- 18:55:59 的启动日志记录先加载 `0071` 插件，再加载游戏模块；崩溃上下文的已加载模块列表同时包含 `0071` 和 `91614`。

因此，两份插件 DLL 在同一进程内注册同名 `AutoFootstepAnimNotify`，触发 `Cannot replace existing object of a different class`。这是本次构建产物混用造成的问题。

## 处理

保留旧 DLL，将热重载映射 `HotReloadState.json` 归档到本机 `trash/autofootstep-startup-20260913-1908/`，同目录保存旧模块清单及原路径、大小和 SHA-256 记录。然后在编辑器关闭时，构建完整 Editor 目标及其插件依赖，显式传入 `-NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles`，不传入 `ModuleWithSuffix`。

后续通过仓库中的 [Build-Editor.ps1](../Tools/Build/Build-Editor.ps1) 执行普通 Editor 构建：

```powershell
& ./Tools/Build/Build-Editor.ps1
```

脚本在本工程编辑器运行时停止构建，提示先保存并关闭编辑器；不会终止编辑器或自动启动测试。仅使用 `-NoHotReloadFromIDE` 无法抵消显式 `ModuleWithSuffix` 所选择的热重载模式。

## 交付边界

普通 Editor 构建成功，日志位于本机 `Saved/BuildEditor/build-20260913-190058.log`。重新生成的游戏 DLL 与插件编辑器 DLL 均导入同一份 `UnrealEditor-AutoFootstep.dll`，插件模块清单也指向该无后缀版本。

随后并行构建将游戏模块清单更新为 `UnrealEditor-FPSGAME-913200327.dll`；该 DLL 同样导入无后缀的 AutoFootstep。保留这次并行构建产物，没有把游戏模块清单改回较早产物。旧后缀 DLL 留作本机恢复材料，当前引用链不再带入它们。

脚步插件保持启用。游戏模块直接依赖该插件，启动时不要用 `-DisablePlugins=AutoFootstep` 绕过它，否则会出现缺少 `UnrealEditor-AutoFootstep.dll` 的加载错误。

本轮只处理启动崩溃涉及的模块产物与构建入口，保留脚步插件和采集玩法。没有启动编辑器或游戏进行复测，运行复测由用户执行。
