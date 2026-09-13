# 生产工具与温带丘陵采集初版

## 素材可复用范围

本机 `Content/EasyBuildingSystem` 已包含 `BP_EBS_Tree`、`BP_EBS_Mine`、`BP_EBS_ResourcesComponent`，以及斧头、矿镐、工具动作、命中音效和粉尘效果。其蓝图依赖 EBS 的玩家接口、交互组件和资源结构，不能直接替换 FPSGAME 的玩家与冷钢背包。本次复用素材和采集规则，使用原生适配代码接入当前系统。

| 用途 | 当前素材 |
|---|---|
| 伐木斧 | `/Game/EasyBuildingSystem/Meshes/Tools/Polygonal/SM_Polygonal_Hatchet` |
| 矿镐 | `/Game/EasyBuildingSystem/Meshes/Tools/Polygonal/SM_Polygonal_Pickaxe` |
| 铁铲 | `/Game/MilitaryTrench/Assets/3D/Ind_Mine_Tool_Shovel_Old_01/StaticMeshes/SM_Ind_Mine_Tool_Shovel_Old_01` |
| 木材命中声 | `/Game/EasyBuildingSystem/Audio/Sounds/Interactions/Chopping/SC_Hatchet_Hit` |
| 岩石命中声 | `/Game/EasyBuildingSystem/Audio/Sounds/Interactions/Mining/SC_Pickaxe_Hit` |
| 命中粉尘 | `/Game/EasyBuildingSystem/Effects/PS_Dust` |

斧头、矿镐保留 EBS 原有多边形风格，未重制为写实资产。铁铲来自 Military Trench。铲土音效初版借用矿镐命中声。没有接入 EBS 自带玩家、独立资源计数器或示例关卡。

Godot 参考源位于本机归档 `E:/3d/trash/repository-ue5-root-20260910`：`scripts/tools/basic_toolkit.gd`、`scripts/tools/scenic_rock_harvest.gd`、`scripts/voxel_lab/wilderness_editor.gd`。开发前读取了这些规则及已有工具接触画面；没有新启动 Godot。参考其三次命中、3.2 米距离、接触时重新取射线、背包满时保留资源、稳定资源标识及库存与采集状态共同提交的语义。

## 游戏操作

- 初次进入游戏时，每个玩家档案领取一把斧、一把镐、一把铲。优先进入背包；放不下的转入仓库。领取标志随玩家档案保存，不按每次进入地图重复赠送。背包与仓库均放不下时本次领取不提交，可腾出空间后按工具键重新领取。
- `6` 装备或收起伐木斧，`7` 装备或收起矿镐，`8` 装备或收起铁铲。工具须位于背包；在仓库中时需先取出。背包原有默认使用操作也可装备或收起工具。
- 左键挥动一次；有效接触距离为 3.2 米。`F7` 收起工具，原有切换武器操作也会先返回枪械。原有 `1–4` 消耗品栏保持原来的用途。
- 工具是正式背包物品，2×3 格、不可堆叠。可存入仓库、丢弃，再通过现有 `E` 拾取。工具模式不替换枪械槽，收起后恢复当前枪械。
- 菜单、建造模式、死亡和翻越期间不执行采集。命中时依据当前视线判定，不使用按下鼠标时缓存的目标。

## 资源规则

| 对象 | 工具 | 三次有效命中后的产出 |
|---|---|---|
| 温带丘陵树木 | 斧头 | 木材 ×4 |
| 可采独立普通岩块 | 矿镐 | 石块 ×3 |
| 可采含矿岩块 | 矿镐 | 对应矿石 ×2、石块 ×1 |
| 干燥表土 | 铁铲 | 泥土 ×2 |

矿物类型由资源原有种子确定：铁 25%、铜 12%、银 4%、金 2%、普通石块 57%。这是初版平衡配置。超大岩壁不采集；含矿类型当前通过瞄准文字区分，未重制矿脉材质。

表土按世界 XY 平面 2.5 米格记录，一格只能领取一次；陡坡与湿河床不允许铲取。此版本是表层材料采集，没有地形挖空、洞穴、支撑坍塌或河床变形。

每次命中都会保存进度。第三次命中先在档案副本中插入所有产物，空间不足则保持原资源和两次命中进度。材料、命中进度、采尽标志通过现有 ColdSteel A/B 档案的同一次 `CommitState` 保存，不另外建立库存或世界状态边文件。

## PCG 与呈现

资源键为 `世界 GUID:v1:层:候选 ID`，不使用会随流送和删除改变的实例下标。生成点和近处树干碰撞重新创建时过滤采尽资源；换到新世界 GUID 后拥有独立资源状态。现有老档案缺少新增字段时按空状态读取。

采尽时移除命中的局部实例，并调度对应 PCG 单元重新生成；不重新生成整个丘陵。附近树干继续使用原有分区 ISM 碰撞，普通树木不新增常驻 Actor。工具模型、音效、粉尘和工具掉落模型异步加载；瞄准提示仅在装备工具时查询，间隔 0.15 秒。

伐倒效果使用已加载的树木骨骼模型，约 2.8 秒倒下后销毁；没有物理砸人或独立可搬运原木。岩石使用粉尘与源实例移除，没有预破碎碎块模拟。采集完成直接进入背包，因此与旧 Godot 的掉落原木再拾取方式存在明确差异。

第一人称工具暂用独立模型与程序挥动，沿用 Godot 的短起势、斜向接触和回收节奏。斧、镐挥动 0.68 秒、0.24 秒接触；铲子 0.82 秒、0.32 秒接触。已读取 EBS 2.1667 秒、65 帧动作信息，但未将其完整人体动画直接用于当前第一人称手臂；本次没有新制握持手臂。

## 文件与恢复

- 工具目录：[production_tools.json](../Content/ColdSteelData/production_tools.json)。
- 工具表现与导出入口：[Production](../Source/FPSGAME/Production)。
- 背包与保存适配：[ColdSteelProductionTools.cpp](../Source/FPSGAME/UI/ColdSteelProductionTools.cpp)。
- 世界资源适配：[TemperateHillsProduction.cpp](../Source/FPSGAME/WorldGeneration/TemperateHillsProduction.cpp)。
- 掉落物适配：[ColdSteelPickupProduction.cpp](../Source/FPSGAME/UI/ColdSteelPickupProduction.cpp)。
- 用户要求的本地素材读取脚本：[read_asset_sources.py](../Tools/ProductionTools/read_asset_sources.py)。

本地 PNG 图标放在 `Content/ColdSteelData/ProductionTools`。斧、镐导出原有 EBS 图标纹理，铲子导出素材包已保存缩略图，不创建验收渲染。恢复本地 Fab 内容并构建 Editor 后，可运行 `UnrealEditor-Cmd.exe FPSGAME.uproject -run=ExportProductionIcons -unattended -nop4 -nosplash -nullrhi` 重新导出。

工具模型、声音和效果目录已加入 `DefaultGame.ini` 的烹饪内容列表；JSON 与 PNG 沿用已有 `ColdSteelData` 运行时文件打包规则。Fab 原始和派生二进制素材留在本机，不随公开源码发布。

## 交付状态

已完成源码与素材路径接入。三款图标导出完成，日志包含 `PRODUCTION_ICONS_EXPORTED`；命令行进程因工程已有 GameFeatureData 配置与 HTTP 8000 端口占用错误返回 1，导出函数已完成写入并返回成功。此结果不代表运行验收。

本机工作树必要构建：`FPSGAMEEditor Win64 Development` 成功（模块后缀 `913951`），`FPSGAME Win64 Development` 成功。最终日志为 `Saved/ProductionTools/build-editor-final.log`、`build-game-final.log`。期间修正了本次句柄前置声明与仅供编辑器使用的 PCG 调用；并行天气、脚步及枪械开发造成的中间构建失败，待对应文件同步后重试完成。

依用户规则未运行游戏、PIE、回归测试或新截图验收；动作位置、采集手感、PCG 删除表现及性能由用户在重启编辑器后测试。
