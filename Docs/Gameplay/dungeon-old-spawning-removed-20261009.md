# 随机地牢旧刷怪清除（2026-10-09）

2026-10-12 后续：按用户新规则单独接入迎宾大厅、分流大厅的普通职员两波遭遇，详见 [大厅两波刷怪](facility-hall-waves-20261012.md)。本页记录的旧导演、精英与 Boss 系统仍保持退役。

用户要求排查“已清除刷怪代码却仍刷怪”，并清空旧机制以便重新设置。

原因已经定位：上次撤下的是 `ADungeonSpawnEntry` 的检修门、井盖和通风口出怪扩展。旧文档明确保留了普通房间和 Boss 系统。正式生成器仍创建并激活 `ADungeonSpawnDirector`，运行服务仍读取 22 个房间的旧怪物池；Boss 泵房还有独立 `boss_encounter` 入场触发器。上次撤下并不等于随机地牢停止刷怪。

本次删除普通房间的编成、精英选择、自动生成、重试、警报与休眠调度以及房间遭遇触发、Boss 入场生成/重新入场重试，删除生成器的创建和激活入口，删除运行服务对旧 `spawn` 配方的读取接口。旧导演与房间遭遇类只保留无 Tick、无计时器、无生成接口的资产兼容空壳，防止历史资产缺类；原实现已备份到 `trash/dungeon-legacy-spawning-20261009/`，包含修改前文件及 SHA-256。

正式目录移除 25 个 `spawn` 字段（22 个怪物池、3 个原本关闭的坡道配置）和泵房的 `boss_encounter`。两处旧清怪推进闸门改为抬起的静态模型，不伪造清房、击杀或奖励状态。终点原类仅保留格栅楼梯/夹层的步行支撑和打开的通道；返程入口正常使用，最终奖励箱仍锁定，等待新规则，不自动赠送原 Boss 奖励。静态检修门、井盖、通风口，房间布局、照明和怪物本体资产保持原状。

作者入口 `SourceAssets/DungeonFacilityFlow20261007/extend_catalog.py` 末尾接入本次清除配方。旧房间源配方属于历史制作输入，重新组装正式目录时会移除其旧怪物设置，避免恢复已退役的逻辑。地图和目录同时保存，原布局银行放置坐标不变，仅更新目录签名。

文件与回执：`SourceAssets/DungeonSpawnReset20261009/recipe.py`、`install.py`，以及 `Receipts/world-before.json`、`install.json`、`source-backup.json`。保存前读取的正式地图没有预放的怪物或旧遭遇 Actor，运行时生成入口与目录仍然完整，是此次继续刷怪的直接来源。

状态以安装回执的 `stage=map_saved` 和本次原生构建结果为准。未启动游戏或进行运行验收。新的刷怪规则尚未实现。

本次常规 `FPSGAMEEditor Win64 Development` 构建已成功，199 个构建动作、136.07 秒，基础 `UnrealEditor-FPSGAME.dll` 已更新。回执为 `Receipts/native-build.json`，日志为 `Receipts/native-build-20261009-232244.log`。这是基础模块构建结果，不是 Live Coding 补丁或运行验收。

正式地图已于本次后台 commandlet 保存，`Receipts/install.json` 为 `map_saved`：25 个旧 `spawn` 字段、1 个 Boss 配置和 2 个清怪闸门规则已移除，目录中相应剩余数量均为 0；布局银行放置结果、灯光参数保持不变。`Receipts/import-20261009-233412.log` 返回 0，汇总 0 错误、8 条既有插件/导航警告，没有材质编译失败。未打开 GUI 编辑器或启动游戏。
