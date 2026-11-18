# 丘陵河湖、树簇与联机修复：整理发布

本批保存自然河曲与终点湖、进村道路自然衔接、树簇和林下伴生、湖岸/河口技术修复、白崖 R9 制作配方，以及客机地标直达、静态地面纠正和内容版本兼容的源码材料。河口与采石场的整体美术仍被用户判为不达标，保持暂停；详见 [待办](../../WorldGeneration/hills-scenery-todo-20261118.md)。

## 发布范围

- `Implementation/` 是本次专属实现的恢复材料，保留原目标相对路径；`Integration/` 是共享宿主的定向补丁。[清单](integration-manifest.json)记录目标、基线及散列。没有覆盖本机真实工作文件，也没有将并行村庄种植、NPC、台地塑形或公共模块拆分整包提交。
- 共享宿主基线有两类：原制作前副本，以及当前共享宿主减去本次增量的上下文。它们都不承诺可直接应用于公开 main。先恢复前置，再按目标逐个合并；不要在已经接入的本机工程重复应用。
- 本机仍以 `Source/FPSGAME` 为实际运行真源。此发布目录不是新的日常开发副本，不把公开材料的存在表述为完整公开游戏已经构建或可以独立运行。
- `Tools/WorldGeneration` 的丘陵构建、截图、联机夹具和白崖制作/导入脚本精确发布。联机脚本默认改为实际通过的 `HillsClosure20261118R2`，扫描预览指向当前 R9；本次未运行它们。

## 恢复前置与顺序

1. 按 [资源恢复](../../AssetSetup.md)恢复 UE 5.8.2、PCG、DynamicWind 等已有项目依赖。读取此前 [丘陵异步入场](../HillsAsyncEntry20261112/README.md) 和 [丘陵植被](../HillsVegetation20261115/README.md) 的本机接入边界。
2. 确认现有 V3 村庄选址、道路保护、河流 FPlan、世界高度采样、采集候选/耗尽、PlayerState RPC 和库存权威路径。共享流送宿主近期拆为 `StreamingPrivate/Preparation/Mesh/Visit/Fog`，本批没有重新发布该并行拆分；补丁须合入实际对应函数。
3. 以清单恢复专属文件，合并 `Integration`。兼容注册须同时带上 `FPSGAME.cpp`、`FPSGAME.Build.cs` 与 `TemperateHillsCompatibility`；地标来宾传送须同时合并 PlayerState 声明、服务端实现、共享落地函数与流送状态。邻域 Floor 可空指针的声明、调用和 `Microhabitats` 定义须一致。
4. 河道与湖岸共享 `SampleChannel`、`NaturalGround` 与 `HydrologyGround` 的连续高度。当前文件拆分前后只能保留一份定义。发布材料裁掉并行的 `UplandReliefCm/BuildUplandRelief` 和村庄种植增量；其公共前置由对应功能单独接入。
5. 按 [本机资源清单](local-assets.json)恢复已授权资产。白崖/采石场原料来自 Quixel/Fab 和项目已有素材；下载许可不代表可公开再分发。UE 包、原始扫描、模型、贴图、Blender/FBX、正式存档和模块二进制都未上传 Git。R9 作者输入及材质母版保留本机。
6. `repair_hills_beech_material.py` 依赖本机 `SourceAssets/BeechHarvestOreFix20261110/install_assets.py` 的 `master_material` 及已修正的 `UTemperateForestAuthoringLibrary::AddVisibilityMaskPin`；只重建三个材质，不导入整棵树。需要重做资产时先确认该前置。构建、导入与按需测试遵守当前用户授权。

## 归档与保留

过期输出移到本机 `trash/hills-scenery-20261118/`。[逐文件清单](retired-files.json)包含原路径、新路径、大小、SHA-256、原因与保留替代物；[归档回执](archive-receipt.json)记录读回结果。共 2904 个原文件、6,454,312,836 字节，其中 40 张检测图片、0 个 GIF。27 个测试宿主联接改存描述文件，生产目标没有移动。此为可恢复归档，不是磁盘空间释放或永久删除。

保留正式 Content、官方世界存档、当前 Binaries、R9 两套 Blender/FBX、QuarryKit、已采用概念图/用户参考、Quixel 原始素材与来源、R2 冻结模块、制作工具和必要小回执。历史文档路径已指向归档；机器外没有 trash 时按清单识别，不把截图当作公共仓库资产。

## 证据边界

[证据索引](evidence-index.json)保留 21 份小型历史回执，原始内部路径是运行时记录，可按归档清单定位。[完成记录](../../WorldGeneration/hills-closure-20261118.md)描述当时本机 Editor/Game 构建、18 项 UDP 检查、五机位完整加载截图及山毛榉材质复拍。失败轮次与成功轮次分开；本批没有重新构建公开源码、启动 UE、运行联机或拍摄截图。公网、专用服务器、全图寻路与用户美术认可不在已有证据之内。

本次 fetch 后，远端领先本地共享 main；原位快进被 Git 因并行修改会被覆盖而拒绝。按 WORKFLOW 第 8 节使用临时发布工作区和精确索引，保留原工作区、分支与暂存区；完成后归档临时工作区资料，不留下日常源码副本。只普通推送到用户指定的 `https://github.com/allang2208/3D-FPS.git` 的 `main`。源码材料及回执上传不等于二进制资源备份。
