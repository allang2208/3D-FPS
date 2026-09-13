# 丘陵云层不可见：密度乘数归零

2026-09-13，UE 5.8.2，`D:/FPS3D/FPSGAME`。

## 已取得的故障证据

用户报告丘陵天空完全没有云。本次读取现有运行日志、编辑器云渲染开关和实际加载的云材质图，不启动新一轮 PIE 或截图测试。

- `Saved/Logs/FPSGAME.log` 的 17:40:12–17:40:13 丘陵记录中，`HILLS_SKY` 已成功启用 `HillsWeatherClouds` 和 `MI_HillsClouds`；随后 `StormClouds: bound` 绑定了同一组件。当前天气为 Clear。不是缺少本地素材，也不是仅创建了一个空云层。
- 编辑器接口读取 `r.VolumetricCloud=1`、`r.VolumetricCloud.Support=1`，云渲染开关正常。
- 修复前 `MI_HillsClouds` 实际参数为 `Cloud_GlobalDensity=0`、`Cloud_GlobalCoverage=0.008`、`StormClouds=0`。其引擎父实例的密度默认值为 `0.008`。
- `Tools/Weather/inspect_cloud_density.py` 只读导出了实际材质节点连接，报告位于 `Saved/CloudDensityDiagnosis/material-wiring.json`。`Cloud_GlobalDensity` 经 Reroute 和 LinearInterpolate 输入标注为 Global Density 的 Multiply 节点；晴天时该插值选择基础密度，因此基础密度为零会抹去整个云密度场。`Cloud_GlobalCoverage` 则进入布局 Add 节点，是另一个语义不同的参数。
- 原 `UStormCloudComponent::UpdateCloudLayer` 每次更新丘陵云层都写入零密度；其他地图进入天气覆盖时也会向零密度插值。只改素材，随后仍会被运行代码覆盖。

## 修复

- 基础密度恢复为 `0.008`，风暴目标密度设为 `0.010`，运行时保持正值。
- 丘陵覆盖率分开控制：晴天 `-0.18`、多云 `-0.04`、风暴 `0.045`。沿用现有风位移、噪声、层高及采样预算。
- 重写本地 `Content/WorldGeneration/TemperateHills/Sky/MI_HillsClouds.uasset`，同时修正其制作脚本，避免重新制作后复发。原资产在 `Saved/TemperateSky/Before-*` 中保留备份。
- 云绑定日志补充素材密度、基础密度与风暴密度，后续可直接定位零密度。
- 更正旧天气审计中“密度必须为零”的错误条件，以及天气技能中把密度称为偏移量的错误描述。本次没有运行该审计。

## 保存与构建

独立资产命令行首次保存遇到编辑器文件占用；编辑器接口修改了内存参数，但当前 PIE 阻止资产保存。用户结束试玩后，命令行于 17:53:39 保存成功，`CloudDensityAssetRepairFinal.log` 记录了实际包移动及 `TEMPERATE_SKY_AUTHORING_COMPLETE`。该命令行仍因工程已有的 GameFeatureData 配置错误返回 1；不能把整个命令行描述为无错误通过。

最终原生 Editor 构建成功：`Saved/Logs/CloudDensityBuild-913864.log`，输出 `UnrealEditor-FPSGAME-913864.dll`。之前两次构建遇到并行采集模块尚未补齐的接口及重载错误，待该模块更新后完成最终链接；本次没有修改采集模块。未执行游戏视觉或帧率测试，云形状和场景观感由用户实测。重新打开编辑器后加载更新的原生模块与材质。

源码仓库不公开提交引擎材质图导出或 Fab/引擎二进制资源；本地材质可通过制作脚本恢复。
