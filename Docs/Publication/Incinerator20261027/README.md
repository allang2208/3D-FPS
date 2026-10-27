# 焚化炉整理与发布

2026-10-27。对应 [焚化炉源码审计](../../Building/incinerator-upgrade-20261027.md)。本次收尾整理废案、沉淀技能并发布源码资料；没有重新构建、运行游戏、试听或进行联机测试。

## 发布内容

- 直接进入运行树：`VoxelBuildPrefabActor.*` 的权威表现结束时刻；`FluidPresentationSubsystem.*` 与 `FluidIncineratorPresentation.cpp` 的黑烟、声音、距离／数量预算和清理；`DefaultGame.ini` 中仅新增焚化声音的 Cook 目录。共享高炉文件中未发布的材料改造没有夹带。
- 直接进入工具：`Tools/IncineratorUpgrade/author_audio.py`、`import_audio.py`、`publish_audio.ps1`。音源为原创程序合成，无外部录音采样；发布制作配方，不公开 WAV 或 UE 包。
- `patches/` 保留 8 个库存接入增量：请求枚举、权威分派、暂存模型、交付前确认 UI、普通档案上传规范化和回执／重连绑定清理。补丁从本轮保存的实际前置快照提取，排除了并行元素箭、食物时钟及其他档案改动。
- 两处技能主题：永久销毁与弹药暂存恢复；短时炉体烟火与声音生命周期。个人技能维护源和工程镜像同步，历史构建与未运行测试的边界分别记录。

## 库存补丁前置

[integration-manifest.json](integration-manifest.json) 记录每个目标文件、补丁、归档基线和规范化 SHA-256。规范化为去除 UTF-8 BOM、CRLF 转 LF，然后以 UTF-8 计算散列。补丁不会自动应用。

公共基线并不包含当前本机完整的库存事务声明和实现，例如 `CommitCampfireState`、`IsCampfireInventoryPending`、弹药暂存标记及相关状态；当前请求枚举还存在未发布的 `Planting` 前置。不能把整份本机宿主覆盖到公共分支，也不能将增量直接盲套到任意旧 HEAD。恢复时先取得匹配的库存事务／档案前置，再核对基线散列并合入 8 个补丁，保持枚举线协议顺序、请求／确认两端版本一致。

直接发布的炉体表现需要上述成功提交路径触发；仅取得表现源码不代表公共库存流程已完整接通。完整本机工程已经接入，但本次公开切片未在隔离克隆中构建，完整 UE 内容及部分玩法前置仍是本机恢复依赖。

## 音频与资产恢复

正式声音：`/Game/Building/Incinerator20261027/S_IncineratorCombustionLoop`。本机已保存包的 SHA-256：`39922d3973f0fc1c78ae3650d8a243e0850ac43541cd607615fd095a89ce0523`。源为 48 kHz、单声道、8 秒循环；重新导入后的 UE 包可能因引擎序列化产生不同散列。

1. 用带 NumPy 的 Python 运行 `Tools/IncineratorUpgrade/author_audio.py`，生成本轮目录中的 WAV 与作者回执。
2. 需要重新导入时，准备 `SourceAssets/IncineratorUpgrade20261027/AssetHost/AssetHost.uproject`，使用下面的最小项目描述；不复制本机生成的网络／安全配置。现有本机宿主描述、已导入声音及正式包仍保留。
3. 在项目既有 UE 批次互斥 `Local\CodexUeMcp-Port-8000` 内，使用 UE 5.8 的 `UnrealEditor-Cmd.exe`、该独立宿主、`-run=pythonscript -script=<绝对路径>/Tools/IncineratorUpgrade/import_audio.py` 完成后台导入，配合 `-unattended -nop4 -nosplash -NullRHI`。脚本只接受这个宿主路径；正常开发不为查看结果启动交互编辑器。
4. 导入保存成功后运行 `publish_audio.ps1`。它持有批次互斥；正式目标存在且散列不同则停止，保留已有资产。仅有脚本或 WAV 不等于资产已导入。
5. 黑烟复用既有 `/Game/Fluids/FurnaceSmoke20260924/NS_FurnaceBlackSmoke`；炉体网格、共享烟雾及其材质仍按原恢复链保留，不在此包中再分发。

```json
{"FileVersion":3,"EngineAssociation":"5.8","Plugins":[{"Name":"PythonScriptPlugin","Enabled":true},{"Name":"EditorScriptingUtilities","Enabled":true}]}
```

## 归档与验证范围

37 个旧文件移入 `trash/incinerator-retired-20261027/`：初次与二次修订前的源码快照、过期自动构建备份、已完成声音导入宿主的缓存／日志。逐文件原路径、目标、大小、SHA-256、原因及保留替代物见 [archive-manifest.json](archive-manifest.json)，移动后已读回校验。正式 C++、当前音频、制作脚本、最终构建回执和首轮编译错误证据继续保留。

上一轮完整本机 Game／Editor 构建最终均成功，最后调用均为目标已最新；没有实际双人联机、延迟／丢包、断线重连、试听或画面验收。本次只进行仓库归档、补丁归属、文本／敏感信息／大小和 Git 发布检查。暂存内容使用独立索引，在原工程直接提交，保留其他任务的工作文件和暂存；只普通推送 `HEAD:main`，成功后回读远端分支与旧 Godot 归档标签。

WAV、UE 包、模型、引擎／插件、导入与构建日志、EXE／DLL、临时宿主、备份和 trash 均不在公开提交中。
