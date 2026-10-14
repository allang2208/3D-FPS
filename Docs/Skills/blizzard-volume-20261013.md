# 暴风雪立体范围与分层云雪（2026-10-13）

用户要求暴风雪覆盖 Z 轴上的目标，并明确完整楼板仍阻挡，只在开放楼梯、中庭等无遮挡空间跨高度生效。

## 伤害范围

- 水平范围继续使用施法快照中的椭圆半轴 `RadiusX / RadiusY`；垂直范围为落点上、下各 `H = RadiusY * 2.3 + 150` cm。这是有界的椭圆柱体，H 随现有技能半径成长，不是无限高度，也不是穿楼板伤害。
- `BlizzardEnvironment::VolumeExposure` 使用身体多点及最近碰撞点，同时判断椭圆、上下高度和无遮挡视线。不再依赖脚底贴地、某个地面单元或原有地面高差限制，因此跳起、悬空及不同台阶高度的目标均可参与判定。
- 传播起点位于施法落点上方 35 / 90 / 150 cm，并受该点天花板约束；起点不会被抬到完整楼板上方。到目标身体任一点存在有效直线路径才会命中，实墙、关门和完整楼板仍阻挡；不会绕墙、绕楼板拐角扩散。
- 继续复用 `MagicOcclusion` 的真实孔洞、多点身体采样和独立栏杆标记。伤害由服务端每 0.5 秒结算，保留原阵营、去重、结束时机、修炼与奖励入口。装饰冰块及雪花碰撞不决定伤害。

## 环境与表现

- 服务端每 0.5 秒采样 5×5 个水平位置；每列最多保留 3 个从施法点可见的地面层，按距落点高度排序。每列下降探测最多 12 次、最多收集 4 个候选面；每个有效层都有各自地面、物理净空和墙边宽度。未命中的地面不伪造为空中平台。
- 房间复制数据由 25 个单元扩为 75 个；客户端读取同一数据。每个存在有效地面的表现层有独立云、降雪、寒雾和地霜。普通单层仍只激活一组，多层最多激活三组。3 层是特效预算，伤害不依赖此层数或地面格采样是否成功。
- 云继续复用现用雷暴五层发射器，保持每层 48 个核心云团及边缘云；雷暴源云、材质和近手凝聚云不改。新增的四邻点插值只平滑同层台阶高度，不将相差 180 cm 以上的地面混在一起。云高度在地面采样更新之间平滑过渡，楼层切换与无效单元直接重置，实际天花板降低时立即裁切。
- 开放处云顶以各层地面加 H 定位，低顶取当地净空并压薄；狭窄净空仍保留原有云渐隐、短程降雪和贴地寒雾。覆盖位置固定在施法落点，地面和净空会动态重采样，释放后不随玩家移动。
- 24 个落冰和 24 个碎片槽在所有层之间共享，不按层翻倍。碎片保留来源层号；装饰几何查询和声音限流沿用原实现。最坏情况下区域 Niagara 数由 3 个增至 9 个，未进行性能测试。
- 地面瞄准预览与合法落点继续沿用原地表规则；预览圈表示水平覆盖，不表示允许穿过楼板。

## 制作入口与交付

原生实现：`Source/FPSGAME/Skills/BlizzardEnvironment.*`、`FPSBlizzardZone.*`。

云作者：`Tools/Skills/build_rolling_storm_clouds.py` 的 `blizzard()`；定向后台入口 `Tools/Skills/build_blizzard_volume_cloud.py`。目标资产仍为 `/Game/Skills/StormClouds/RollingV1/NS_BlizzardStormCloud`，保存回执位于 `SourceAssets/BlizzardVolume20261013/asset-authoring.json`。

云资产已通过 Python commandlet 实际编译保存，进程退出码为 0，回执为 `stage=assets_saved`；日志 `Saved/BlizzardVolume20261013/asset-commandlet.log` 包含 `BLIZZARD_VOLUME_ASSETS_SAVED`。不是仅生成制作脚本。

本轮 `FPSGAMEEditor Win64 Development` 构建成功，包含最终分层碎片与云层平滑代码，日志 `Saved/BlizzardVolume20261013/Editor-console.log`。游戏重链曾因同期新增库存网络接口缺少实现而失败，记录在 `Game-final-console.log`，未改动该并行开发模块。新库存实现落盘后，工程后续 `FPSGAME Win64 Development` 完整构建成功，实际产物和结果记录在 `Saved/WoodworkingSelectionCards20261013/Game.log`（181 项动作，196.56 秒）；最终暴风雪代码已进入游戏程序。

用户要求继续后执行最终编辑器构建，退出码 6；当前工程最终全量状态不能称为构建完成。`Saved/BlizzardVolume20261013/Editor-final-console.log` 记录共享库存模块 `ColdSteelSharedInventorySubsystem.cpp` 的接口错误：`AColdSteelPickup::InitializeSharedItem / IsSharedPickup`、`ColdSteelWorldInteraction::CanReachPickup` 缺失，以及 `ColdSteelCompartment::Place` 无法解析。未修改或回退该并行模块。上述较早的编辑器成功产物包含本次暴风雪改动，但不代表当前全部工程源码能构建；云资产实际保存和游戏版本成功状态不受此表述混淆。

没有启动 GUI 编辑器、游戏、实机测试、截图或渲染；构建与资产编译保存不代表运行效果或性能验收，交由用户测试。
