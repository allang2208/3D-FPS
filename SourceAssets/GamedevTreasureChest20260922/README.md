# 原 gamedev 探险宝箱迁移 · 2026-09-22

2026-09-23 用户反馈棋盘格和实心箱口后，结构与材质绑定已进入后续修订；当前制作源及导入记录见 [三维结构与材质修订](../GamedevTreasureChest20260923/README.md)。本目录保留首次迁移和开盖动作来源，不以旧实心模型覆盖后续空心容器修订。

用户要求：迁移原项目宝箱，并与当前仓库宝箱区分。

## 身份与来源

- 使用原项目 `tools/ai-gen/_settlement_building_pack_20260821/dungeon_chest_closed/dungeon_chest_closed_model.blend` 和 `dungeon_chest_open/dungeon_chest_open_model.blend`；源目录位于 `E:/无尽轮回/长期备份/2026-7-13-1/game-dev`。
- 正式图片参考为 `assets/terrain/chest_closed.png`、`chest_opened.png`。图片是在 Blender 几何源上进一步细化的 2D 成品，本次迁移真实三维网格，不声称原图片中的纹理细节全部搬入了模型。
- 完整原文件副本、UE 工作源、FBX 和参考图都保留在此目录。仅在用户自己的项目内复用，不作外部分发。
- 探险宝箱使用黑铁箱体、古金边框、钥匙孔、卷草、侧提手、拱盖及顶盖徽章；仓库仍使用现有仪式风格的白石／宝石箱，不改其模型、材质、UI、存档或交互。

## 制作

- 原几何按 0.65 比例统一适配，约宽 149、深 119、高 110 cm；地面枢轴，+X 为正面，保留原模型非对称侧提手。
- 箱体与盖子刚性分配到 Root／Lid 两根骨骼，沿原后铰链保留 58° 开盖姿态。
- 首轮迁移保留闭合／开启两个端点姿态片段；后续按用户“帮我接入”补做连续开盖动画，详见下方。
- 同时交付闭合、开启两个静态网格，方便直接摆放。骨骼网格供现有地牢生成器使用。
- 三种独立材质：黑铁、古金、暗色内衬，添加轻微金属粗糙度变化，无仓库蓝色发光。
- 资产根目录：`/Game/Props/GamedevTreasureChest20260922`。

## 接入

- 专用配置：`Content/ColdSteelData/treasure_chest_assets.json`；与 `warehouse_assets.json` 分离。
- `DungeonTreasure20260922/Scripts/extend_catalog.py` 改为读取专用宝箱配置，后续重建不会重新套用仓库箱。
- `install_treasure.py` 只更新随机地牢的 treasure_chest 条目和既有 DungeonTreasureChest 视觉，不重新生成整个地牢，不增加奖励或开箱业务。
- 箱体碰撞由宝箱自己的尺寸配置提供；缺少配置的既有条目继续沿用原碰撞尺寸。
- 开盖静态网格与端点姿态继续保留。宝箱开盖交互见下方，奖励仍保留 `FutureTreasureLoot` 占位用途；不迁移掉落、钥匙或存档数据。

## 交付状态

具体导入和地图保存结果记录在 `materials_receipt.json`、`import_receipt.json`、`install_receipt.json`。仅有源文件不代表完成 UE 接入。

三种材质、骨骼网格及其骨架、两段端点姿态、两套静态网格已导入保存；见 `materials-import-7.txt` 和 `meshes-import-2.txt`。

`/Game/GameMaps/L_Dungeon_Randomized` 已保存：更新 1 条宝箱生成配置，并替换地图中已有的 2 只宝箱视觉、朝向和碰撞盒；见 `install-map-3.txt`、`install_receipt.json`。没有重生成整个地牢，没有修改仓库模型和配置，没有改动掉落规则。

用户未授权测试或预览，本次不启动 PIE、不制作预览渲染、不运行测试，交由用户测试；必要资产编译和原生构建另行记录。

### 原生构建

常规 `FPSGAMEEditor Win64 Development -WaitMutex -NoHotReloadFromIDE` 必要构建已成功，基础 `UnrealEditor-FPSGAME.dll` 已包含宝箱碰撞配置的读取改动。首次构建遇到的性能面板 C4458 在最新工作区中已经修正；本任务没有改写该性能面板，也没有强制关闭其他编辑器。

模型／姿态／材质继续使用已有引擎类型，不引入新的原生宝箱类。构建成功不等于游戏测试或视觉验收。

## 连续开盖与 E 交互 · 后续接入

- 参考了原项目正式闭合／开启图片、原后铰链姿态和 `chest-room-system.js` 的状态切换。原版是 140 ms 淡出 + 260 ms 淡入，两张图片单次切换；没有可直接迁移的连续三维动作。
- 新制作 `A_TreasureChest_Opening`：30 fps、31 个采样点、1 秒、非循环。先短暂停顿 0.08 秒，0.70 秒抬盖至 60°，0.22 秒轻微回落至原来的 58°。箱体不移动，盖子及其金属附件随 Lid 骨骼运动。
- 可编辑源：`Authored/GamedevTreasureChest_Opening.blend`；引擎导出：`Authored/A_TreasureChest_Opening.fbx`；生成脚本：`export_opening.py`。原闭合源文件和两段端点姿态保留。
- 专用配置的 `opening` 指向连续动画；`open` 仍是固定开盖姿态，`close` 仍是固定闭合姿态。生成目录的 `opening_animation` 和地图的 `module_assets` 提供预加载与资产引用，烘焙沿用现有宝箱目录。
- 复用 `ColdSteelWorldInteraction` 的准星射线、2.5 m 眼部距离、遮挡和单机限制，在现有 E 输入分支触发。地图既有及随后生成的 `DungeonTreasureChest` 都适用，无须更换 Actor 类型。
- 提示复用现有冷钢 HUD：关闭显示“E · 探险宝箱 · 开启”，动画中显示“探险宝箱 · 开启中”，结束显示“探险宝箱 · 已开启”。不会打开仓库面板。
- 开启中／已开启会消费 E，但不会重播动画。动画期间启用骨骼更新，离开视野也继续播放；结束后主动求值末帧并停用骨骼 Tick。结束计时器弱绑定箱子生命周期，地牢重建或切图销毁箱子后失效。
- 开启状态只属于当前宝箱实例，重建地牢后新宝箱闭合。本次不增加存档、奖励、音效或关盖业务。
- 未启动 PIE、未运行测试、未渲染预览；由用户测试。动画导入、地图保存和本次必要构建结果另记实际输出。

### 本次接入结果 · 2026-09-23

`opening-import-1.txt` 记录连续动画及专用配置已经保存。首次地图接入遇到未保存的关卡，在修改地图前停止；随后使用 `install_opening.py` 完成目标关卡的单项引用更新，未重建地牢或重新替换模型。

`opening-install-map-20260923-1.txt` / `opening_install_receipt.json` 记录 `/Game/GameMaps/L_Dungeon_Randomized` 已保存，更新 1 条宝箱生成配置及动画硬引用。地图既有宝箱沿用原类型和标签，由已接入的 E 逻辑处理。

常规 `FPSGAMEEditor Win64 Development -WaitMutex -NoHotReloadFromIDE` 必要构建成功；UBT 报告目标已是最新，0 个编译动作，记录在 `opening-build-20260923.txt`。完成构建后打开编辑器用于上述地图保存，未启动游戏测试。
