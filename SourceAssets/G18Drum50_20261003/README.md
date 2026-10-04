# G18 大弹鼓（50 发）

## 制作范围

- 仅用于 G18，枪匠配件标识为 `g18_drum_50`，槽位为 `magazine`。
- 容量为 50 发；按 G18 原厂 17 发计算，`mag_delta` 为 33。
- 用户于 2026-10-03 指定金色限定卡、换弹耗时增加 50%、开镜耗时增加 15%。目录使用 `reload_mult: 1.5`（空仓换弹继承该倍率）和 `ads_percent: 0.15`；不改武器基础数据及其他配件。
- 按用户提供照片制作长供弹颈、厚圆鼓、三辐端盖、外圈锁扣和加强筋。按用户选择省略外接电池、电线与插头。
- V2 按用户纠正，鼓体在武器根坐标中俯视顺时针旋转 90°（绕 Z 轴 -90°），由横跨枪身左右改为沿枪身前后；供弹颈与原厂插接段不旋转，连接座重新建模。
- 三辐端盖改为单张连续曲面上的浅凸筋，增加圆滑根部、中心环槽、卷边、贴壳弧面锁扣、凹入紧固件、分模缝与收腰连接座。供弹颈单独使用黑色涂层材质，不改变原 G18 材质。
- 背面未在参考图中完整展示，采用与可见外壳一致的维护盖和加强筋设计。
- 本资产是游戏外观模型，不包含机械供弹机构。

## 来源与编辑

用户参考图保存在 `Reference/user_drum.png`，仅作为本项目制作参考，不将其视为开放许可图片。供弹颈的原厂插接段来自项目已有的 `SourceAssets/G18Integration20260929/Single/G18_single_Editable.blend`，继承原 G18 来源记录。鼓体为本次本地建模。

可编辑源为 `G18_Drum50_Editable.blend`。保留 G18 骨架参考坐标，挂到 `WPN_SOCKET_Magazine` 时使用现有逆绑定变换；不要单独把导出模型重新居中。

制作脚本按以下顺序使用 Blender 后台执行：

1. `author_drum.py`：调用 `drum_surface_v2.py` 制作鼓体细节、独立旋转及重建连接座，完成 UV、贴图烘焙和独立 LOD 导出。
2. `render_icon_source.py`：用原 G18 UV 和纹理制作供弹颈黑色涂层，并制作图标底图。
3. `package_lods.py`：输出带 LODGroup 的正式 FBX 以及 GLB。

图标由实际模型底图和现行灰阶金属框参考通过 imagegen 制作，保存在 `Icons/ue_g18_magazine_g18_drum_50.png`。

## 交付文件

- `Exports/SM_G18_Drum50.fbx`：用于 UE 导入，包含三个 LOD。
- `Exports/SM_G18_Drum50_LOD0.fbx`、`LOD1.fbx`、`LOD2.fbx`：独立 LOD，具体三角形数量记录在 `authoring.json`。
- `Exports/SM_G18_Drum50.glb`：通用交换文件。
- `Textures/`：2048 像素 BaseColor、ORM 和 DirectX Normal；供弹颈使用原 G18 UV、基础纹理与法线，加独立黑色涂层。
- `authoring.json`：制作来源、导出数量及坐标记录。

## UE 接入

正式资产目录为 `/Game/Weapons/G18/Drum50_20261003`，静态模型路径为 `/Game/Weapons/G18/Drum50_20261003/Meshes/SM_G18_Drum50`。

`import_assets.py` 通过现有 UE 批次互斥桥导入并保存贴图、湿润材质、三档 LOD 静态模型和 UI 图标，再将鼓体材质加入 G18 湿润材质库。只有 `import_receipt.json` 的 `complete` 为 true 才代表整批资产已保存。当前已运行编辑器若在 PIE 中，需先退出 PIE。

资产落盘后运行 `catalog_extension.py`，仅更新 `Content/ColdSteelData/gunsmith.json` 内 G18 的这一项。现有 G18 重建脚本也已保留该专属选项和湿润材质入口。

弹鼓模型沿用手枪弹匣挂接，覆盖单持、双持副手、枪匠预览及共用展示路径。大弹鼓不进入步枪弹鼓的抛匣时序。

单持普通/空仓换弹新增 `Reload/` 制作批次：参考 AKM PalmGripV3 的掌心托底与四指包握，将其掌面关系按 G18 当前鼓壳和原生手骨坐标重新配准，保留骨长与右手、枪体、弹匣轨道。取鼓时先张手再逐指闭合，插入后先松指、向外退手，再回握或接回空仓套筒尾段。双持保持既有单手换弹动作。

运行时仍播放原 G18 基础序列，通过 `/Game/Weapons/G18/Drum50_20261003/Reload/DA_G18_Drum50` 只在装有该配件时叠加普通/空仓两条左臂差量。改 `Reload/author_reload.py` 后须重新导出并执行 `Reload/import_reload.py`，该入口同步重制共享 Profile；不能只改 FBX。源时长仍为 1.75 / 2.25 秒，增加的耗时由游戏换弹时钟统一计算。

卡片复用 `M4GunsmithLayout.cpp` 的冷钢金色限定样式，以 `ue_g18 / magazine / g18_drum_50` 精确组合判定；模型与图标保持原有黑色/灰阶外观。

## 当前状态

V2 模型、贴图、图标和接入源码已完成。方向修正前的 V1 已于 2026-10-04 移入本机 `trash/attachment-effects-20261004/SourceAssets/G18Drum50_20261003/Revisions/V01/`，原路径、大小与散列见 [归档清单](../../Docs/Publication/AttachmentEffects20261004/archive-manifest.json)。本次 C++ 改动已包含在 2026-10-03 21:15:26 开始、结果为 Succeeded 的 FPSGAMEEditor 构建中，见 `compile_receipt.json`。

后续金色限定卡与左手换弹配置选择已通过常规 FPSGAMEEditor 构建，当前 DLL 已更新，见 `Reload/compile_receipt.json` 与 `Reload/native-build-3.log`。50 发、换弹 +50%、开镜耗时 +15% 已发布到目录。普通/空仓两条作者动画与 `DA_G18_Drum50` 已实际导入保存，共享制作器报告 ready=True、retained=0、pending=0；见 `Reload/import_receipt.json`、`Reload/install_receipt.json` 与 `Reload/import-mcp-2.txt`。

用户明确授权后已结束当时的 PIE。V2 模型、三档 LOD、三张贴图、鼓体和供弹颈两种材质、湿润材质库及专属图标均通过现有编辑器保存，`import_receipt.json` 的 `complete` 为 true。G18 枪匠目录已发布 `g18_drum_50`，容量为 50 发，见 `catalog_receipt.json`。未主动打开、重启编辑器或启动游戏。

本轮按用户要求重新对照了原图和实际模型方向与细节。未运行游戏或进行运行测试；换弹接触与实际游戏外观交由用户测试。
