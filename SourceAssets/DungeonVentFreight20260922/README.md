# 环廊通风机房与错层货运中转间

制作依据：`Docs/Gameplay/dungeon-two-room-proposal-20260922.md`，用户已批准构建。

## 内容

- `VentilationLoop`：18×16 m 削角轮廓，6×8 m 贯顶封闭机芯，左右环路，错位双接口；两组带护网和扇叶的风机、检修面板、滤芯维护架、压差表、软接和矩形风道。
- `FreightTransfer`：18×18 m 包络的 T 形，18×10 m 后厅与 10×8 m 前厅，0.6 m 卸货台、两组四级台阶、旧货梯门、防撞构件、停靠葫芦、托盘与托盘车。
- 两个房间各有 3 m 宽、2.8 m 高的入口与出口，接口地面相同标高。主体不缩放；墙、地、顶、柱梁、五金、灯具和内容锚点随完整房间转向。
- 沿用真实已认可的碎瓷砖墙面与材质；共用 `DungeonTileFracture20260922`、`AtmosphereV2`、`RoomInteriors` 和当前管件材质依赖。
- 本批几何为本地精确建模，不复用被否决的 5080 地牢候选。继承材质仍遵守原有来源与发布边界。

## 真源

`Config/rooms.json` 保存建筑轮廓、标高、接口、灯具、锚点与主体参数；`Scripts/author.py` 保存细部制作规则。可编辑模型为 `Authored/Dungeon_VentFreight.blend`，单组 FBX 与 `Authored/manifest.json` 一并保留。

材质绑定在 manifest 中，不把 Blender 中的临时材质色当成引擎最终外观。墙面原有逐角 UV、破损尺度和材质继承记录在 `Authored/surface-provenance.json`。

## 重建与接入顺序

1. 系统 Python 3.11 执行 `Scripts/prepare.py`。
2. Blender 5.1 后台执行 `Scripts/author.py`，加 `--python-exit-code 1` 以传播制作错误。
3. 通过工程 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript`，依次运行 `Scripts/import_vent.py` 与 `Scripts/import_freight.py`。引擎目标为 `/Game/Dungeons/VentFreight20260922/Meshes`。
4. 导入完成后执行 `Scripts/build_extension.py`；生成 `Config/modules.json`，并把本批注册至 `DungeonRoutes20260922/Config/room-extensions.json`。现有目录构建脚本保留扩展钩子。
5. 首次接入需编译 `AuthoredDungeonGenerator.cpp` 的目录驱动选房逻辑。本次没有新增原生类或修改 UPROPERTY 结构；可由 `Scripts/compile_room_pool.py` 同步 Live Coding。常规构建也会包含源码修改。
6. 经同一桥执行 `Scripts/install.py`，在 `/Game/GameMaps/L_Dungeon_Randomized` 的原生成器目录中追加两房和资产硬引用，保留现有模块、材质覆盖、起始段与生成规则，装配并保存目标地图及其外部 Actor 包。

`install.py` 不运行原整场安装器，避免重新替换起始柜子、神像或重置原照明。场景中有未保存的地牢改动或正在播放时保留现场，停止该次接入。接入前目录保存在 `Sources/catalog-before.json`。

用户要求保持 UE 关闭时，可用 `Scripts/build_extension.py --prepare-only` 生产离线目录：写入本批明确的目标路径，但不注册到活动房间库、不修改关卡。此模式不表示所有引用的资产已经导入。完成剩余导入后，按第 4 步注册，再接入地图。

## 状态口径

模型导出结果见 `Receipts/author-02.log`，引擎导入以 `Receipts/import.json` 的 `meshes_saved` 为准；地图接入以 `Receipts/install.json` 的 `map_saved` 为准。连接中断或失败批次不视为完成。

没有运行自动测试、PIE、截图、渲染、导航或走位验收；由用户进入 `DUNGEON / Random Routes` 自行体验。210–235 m² 为批准方案的可走面积设计目标，并非本轮实测导航面积。货梯为封闭背景，风机为静态机械构件；本次不新增升降、解谜门禁、遭遇或奖励逻辑。
