# 丘陵夜袭传送门与神像守护

2026-11-15。复用现有门框、护士僵尸、胖子僵尸、怪物行为树与前院随机神像。本次不刷新世界种子，不改主神空间旅行门。

## 门与夜间生成

- 独立出怪门沿用原大理石／金属门框。中央使用独立的双面紫色光幕：深紫底、向上流动的紫罗兰雾带、反向细流、浅紫边缘，8 秒展开、黎明 4 秒收束。光幕遮住门内，碰撞只属于实体门框。没有旅行交互。
- 权威天气时钟的 19:00—06:00 为夜袭时间。每夜在村庄东西入口以外的干燥缓坡选一个位置，避开水体、实体障碍及玩家 35 m 内范围；面向村庄神像。位置由世界种子和天气日编号决定。
- 开门后预热 12 秒；每 30 秒一批 3 只，批内每 2 秒出一只。顺序为两只护士僵尸、一只胖子僵尸，沿用实际模型、动作、属性、受击、死亡与奖励。
- 同时存活上限 12，每夜生成总量上限 36。达到存活上限时等待空位；失败每 3 秒重试，不消耗额度、不累计补发多个夜晚。出生点需有真实导航路径和空闲胶囊空间，玩家贴门 6 m 内暂缓该次出生。
- 黎明关门停刷；存活怪物继续寻找玩家，死亡后沿原怪物尸体寿命回收。下一夜重新选门址，存活上限跨夜计算。

## 决策与受击合同

| 优先级 | 条件 | 行为与退出 |
| --- | --- | --- |
| 1 | 死亡、眩晕、击倒、既有攻击执行阶段 | 沿共用行为树和怪物执行组件处理，保留打断、接触时刻和单次命中去重。 |
| 2 | 看见玩家、听见有效线索或受到玩家攻击 | 沿原感知规则追击／调查，不受出生点的普通返回距离限制。近战仍要求距离、高度和遮挡满足。 |
| 3 | 暂无有效玩家记忆，且神像在夜间可攻击 | 沿 NavMesh 向前院神像推进，以原有攻击动画和伤害入口扣除神像耐久。 |
| 4 | 神像已失效，或处于白天 | 在村庄神像周边的导航点搜索，继续视听感知和受击反应；不会直接读取未发现玩家的位置。 |

神像为 1800 耐久。仅本次夜袭怪物的有效攻击扣耐久；玩家伤害不会误伤神像。归零后模型保留，交互提示“赐福中断，黎明恢复”，当前丘陵赐福效果和新领取暂停。06:00 恢复完整耐久及已有赐福；原领取事务不清空，所以不会重新领取即时治疗。白天神像受保护。

夜袭调度与耐久属于当前丘陵会话，跟随现有天气会话时钟；本次没有增加独立跨会话夜袭存档。既有世界种子、人物存档和神像领取回执保持原语义。服务器生成与扣血，复制门的时钟、怪物、神像耐久和夜间状态，晚加入客户端读取当前状态。

## 地形与导航接入

正式丘陵地图使用独立 `HillsNavigationSystem`，只围绕导航调用者生成动态网格；新增范围覆盖当前 1024 m 高度场，复用既有 Nurse 和 HandBrain 两种代理。胖子使用可容纳其胶囊的 62／204 cm 代理，护士保留 34／184 cm 代理。地图导航配置实际保存，导航地面由运行时已完成碰撞的详细地形提供。

村庄保留半径 140 m 的详细地面；怪物与选定门址周边保留 60 m 地面。树干碰撞同样参与导航。此供给不添加玩家植被生成视角，不扩大草木可见半径。生成器仍使用现有每帧提交／卸载和并行地形作业预算；导航资源随怪物回收与换图清理。

## 文件与交付边界

- 参数：`Config/DefaultGame.ini` 的 `[TemperateHills.NightRaid]`；`Enabled=False` 可暂停夜袭。
- 运行：`HillsNightRaidSubsystem`、`HillsNightPortal`、`MonsterNightRaid`、`ChapelShrine`。
- 光幕源：`SourceAssets/HillsNightRaid20261115/NightPortalVeil.ush`。
- 后台作者：`Tools/WorldGeneration/author_hills_night_raid.py`；材质及正式地图实际保存后产生同批 `authoring-receipt.json`。
- 修改前源码、配置与地图备份位于同批 `Before`。
- Editor／Game 最终后台构建均成功，回执为同批 `FPSGAMEEditor-build.json` 与 `FPSGAME-build.json`（最终日志后缀 `-4`）。
- 后台作者脚本执行成功，已保存 `/Game/WorldGeneration/HillsNightRaid/M_NightPortalVeil` 和 `/Game/GameMaps/L_TemperateHills_Initial` 的地图导航配置及范围；具体保存回执为同批 `authoring-receipt.json`，进程退出码为 0。正式地图修改前已备份。
- 没有启动游戏、PIE、截图、渲染或自动验收，由用户进场测试外观、出生位置、寻路、攻击与联机表现。材质保存与原生构建不代表运行效果已验收。

## 追加：紫色天空光柱

用户要求为怪物传送门增加直达天空的紫色光柱。光柱从门内 180 cm 高处升起，高度 3000 m，外晕总宽 12 m；细亮紫色中心、柔和外晕与向上流动的细纹合成一个连续光柱，顶部最后 28% 渐隐。沿传送门现有 8 秒开启／4 秒关闭时钟渐入渐出，晚加入客户端使用同一复制时钟。

仅增加一个无碰撞、无阴影的视觉组件和 MID，不增加灯、独立 Actor、定时器或寻路障碍。单片 128 三角形网格在材质中按各自观察视角绕世界 Z 轴朝向相机，保持直立，支持多视角；深度遮挡保留，雾逐像素计算，曝光补偿只施加一次。光柱不受近处门灯 45 m 距离裁剪影响，作为地图内远处可见的夜袭标记；实际可见性仍受地形、建筑与天气遮挡影响。

新资产为 `/Game/WorldGeneration/HillsNightRaid/M_NightPortalSkyBeam` 和 `SM_NightPortalSkyBeam`，加入既有异步预载与烹饪目录。作者入口 `Tools/WorldGeneration/author_hills_night_sky_beam.py`，HLSL、网格源、改前备份及本轮交付回执位于 `SourceAssets/HillsNightRaid20261115/SkyBeam`。此追加不改刷怪、伤害、神像、种子和地图包。

本轮 Editor／Game 后台构建均成功（`SkyBeam/*-build.json`，日志后缀 `-1`）。独立作者批次已成功保存光柱材质与网格（`SkyBeam/authoring-receipt.json`，`authoring-process-2.json` 退出码 0），未重存地图。未运行游戏、截图或视觉验收，由用户进场确认实际观感。

<a id="forest-village-night-raid"></a>

## 林道村庄接入 · 2026-11-24

正式地图为 `/Game/GameMaps/L_ForestPathVillage`。夜袭沿用 11 月 21 日完整工程备份的门框、紫色光幕与天空光柱、护士与胖子僵尸、天气时钟、刷怪额度和独立存档。当前地图的城外门址按东、西两处城门和烘焙的林道权重选择；道路满占时会尝试城门外的空地。选址和落地共用地表识别，覆盖村庄地基、带地表标记的外围地形块以及原林道 Landscape。地基碰撞提交后刷新服务端导航，生成时要求有到神像或可攻击防御工事的完整路径。此前村址迁移留下的远端门址会重新选择，当夜已刷数量和剩余波次沿用存档。

[地图选址和刷怪](../../Source/FPSGAME/WorldGeneration/HillsNightRaidSubsystem.cpp) · [存档接入](../../Source/FPSGAME/WorldGeneration/HillsNightPersistence.cpp) · [村庄地基导航](../../Source/FPSGAME/WorldGeneration/ForestVillage.cpp) · [备份复用清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestVillageNightRaid-R1-20261124/reused.json) · [地图接入恢复版本](Y:/备份/FPS3D/HillsForestPath/ForestVillageNightRaid-R1-20261124/ForestVillageNightRaid-R1.zip)。
