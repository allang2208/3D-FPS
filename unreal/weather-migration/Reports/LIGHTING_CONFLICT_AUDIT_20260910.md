# 光源竞争排查（2026-09-10）

## 结论与保存状态

已在 `/Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation` 的真实运行中复现用户截图同款 ForwardShadingPriority 警告。该地图是枪械预览场，两个定向光来自 `SourceAssets/M4InfimaRigRepair20260909/create_validation_map.py`，不是昼夜循环生成的重复太阳。

三张正式游戏测试地图的静态组件检查和独立渲染运行均未发现重复有效太阳或天空光。此次没有改动它们的地图资产或昼夜/天气行为。

**预览地图的修复现已保存并通过重新加载检查。** 前一轮两个并行编辑器打开同一预览地图，保存返回 Windows 错误 32（文件共享冲突）。用户要求先不要关闭，本次继续时占用已解除；全程没有关闭现有编辑器。2026-09-10 10:09:47 再次核对并保存后，日志 `preview-fix-resumed.log` 记录 `PREVIEW_LIGHT_PRIORITY_FIX_PASS`。本轮读取时磁盘的主光优先级已为 1；修复脚本仍核对主光、补光和天空太阳设置，并保存重载确认。

## 复现证据

`Saved/LightingAudit/Preview-before.log` 与 `L_M4RigValidation-before.png`：

- `DirectionalLight_0.LightComponent0`：可见、影响世界，强度 4，前向优先级 0，天空太阳索引 0。
- `DirectionalLight_1.LightComponent0`：可见、影响世界，强度 2，前向优先级 0，天空太阳索引 0。
- 一个有效 SkyLight。
- 实测 `top_count=2`；实际渲染图出现 Multiple directional lights are competing 警告。

UE 5.8.2 的 `LightGridInjection.cpp` 按最高优先级选择前向主光，最高优先级并列时计为冲突；亮度只用于兜底选择。预览补光还与主光共用天空太阳索引 0。

## 三张游戏地图

| 地图 | 有效定向光 | 有效天空光 | 运行控制路径 | 证据日志 |
|---|---:|---:|---|---|
| DayNight_Lighting | 1 | 1 | BP_FPS_DayNightManager；天气只同步时钟 | DayNight-before.log |
| L_Normandy_FPS_Test | 1 | 1 | FPSWeatherManager 驱动导入的现有灯光 | Normandy-before.log |
| L_MilitaryTrench_FPS_Test | 1 | 1 | FPSWeatherManager 驱动现有灯光 | Trench-before.log |

上述日志及对应运行截图均在 `Saved/LightingAudit`，全部记录 `LIGHTING_AUDIT_PASS`、`top_count=1`。已查看三张运行截图，没有该警告。村庄的 RectLight 是局部补光，不参与定向主光竞争；战壕 LevelSequence 的 auto_play 为 false。昼夜蓝图内部两个 SkyLight 是可选路径，运行中只有 Cubemap SkyLight 有效，没有把隐藏的备选组件误计为重复光。

这些运行证据覆盖进入地图并完成初始化后的状态，不等于长时间完整昼夜循环或所有天气组合的视觉验收。

## 已实施修复

1. 当前连接编辑器：主光 ForwardShadingPriority=1；补光保持 0，并关闭补光 AtmosphereSunLight。两灯强度、位置及旋转保持原值。读回证据为 `preview-live-after.json`、`preview-fill-live-after.json`。
2. 已保存的地图生成脚本应用同样设置，防止重新生成时复发。
3. `Tools/SceneTests/fix_preview_light_priority.py` 已执行：核对目标地图及两灯强度、仅修改上述属性、保存后重新加载并断言通过。
4. `Saved/LightingAudit/Backup` 保留修改前地图和相关源文件，并在本轮保存前另存带时间戳的地图备份。没有编辑骨骼、Control Rig、动画或序列资产。

复用修复命令（仅在目标地图未被其他编辑器占用时运行）：

```powershell
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript -script=D:/FPS3D/FPSGAME/Tools/SceneTests/fix_preview_light_priority.py -unattended -nosplash -nullrhi -abslog=D:/FPS3D/FPSGAME/Saved/LightingAudit/preview-fix.log
```

保存及重新加载成功标记为 `PREVIEW_LIGHT_PRIORITY_FIX_PASS`。本轮已重新启动独立预览运行，使用 `-LightingAudit -LightingLabel=after -ColdSteelProfile=LightingAudit_20260910`：`Preview-after.log` 记录两盏定向光、一个天空光、`top_count=1`、`atmosphere_conflict=0` 和 `LIGHTING_AUDIT_PASS`。主光强度仍为 4、补光仍为 2；已查看 `L_M4RigValidation-after.png`，原先的黄色竞争警告消失。验证进程正常退出，现有编辑器未关闭。三张游戏地图沿用上轮已通过的检查证据，本轮没有修改它们。

## 检查工具与编译

`audit_lighting_conflicts.py` 只读地图灯光组件；`LightingConflictValidation.h/.cpp` 提供显式 `-LightingAudit` 才启用的运行检查，10 秒后记录灯光、所属关卡并截图，再正常退出。普通运行不启用检查、不自动退出。`FPSWeatherManager.cpp` 仅增加这个可选检查入口。

最终 FPSGAMEEditor 编译成功，日志 `Saved/LightingAudit/build-final.log`。已存在的 GameFeatureData、MCP 端口和 Niagara 初始化提示与本次光源冲突分开记录，没有用命令行退出码替代通过标记。
