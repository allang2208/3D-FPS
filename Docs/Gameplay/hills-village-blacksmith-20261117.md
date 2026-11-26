# 丘陵村庄扩建与铁匠铺

2026-11-17：村庄由 7 间增加到 9 间，第一间村口小屋改为默认残破的铁匠铺。沿用现有丘陵存档与地形种子，不重建地形。正式子关卡为 `/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage`。

## 布局与陈设

- 08 北侧残破民居：既有 `SL_Packed_House_TypeA_00B`，村庄局部坐标 (-11, -39) 米，门向村内。
- 09 南侧残破长屋：既有 `SL_Packed_HouseTypeB_01A`，局部 (10, 39) 米，门向村内。
- 新增北、南两条 2.2 米支路，以及西、东城门的主路连接段；外围墙、教堂院子和神像保持原有布局。
- 道路贴花、草地排除图和 RVT 道路采样扩至 130×100 米。地形选址使用的旧 `extent_m` 不变，新增 `surface_extent_m` 只控制道路和陈设覆盖。
- 其余住宅布置木床、木桌、储物架和原有木长凳，按房间地板与门位选择墙角，保留门口至室内中央通道。
- 铁匠铺后部为原有铸造台与石质隔火垫，侧墙为材料架和木箱，前部为桌凳；正门上方为横向“铁匠铺”实体木牌，旁边“待修复”小牌只在残破状态显示。
- 新家具与标牌不接收地表贴花。石板、橡木和金属沿用现有材质，标牌使用实体面材质。

## 残破与修复

`AHillsBlacksmith` 继承既有 `AVoxelBuildPrefabActor`，只持有可操作的铸造台；房屋及陈设放在独立场景 Actor 中，因此瞄准房屋墙壁不会被识别为铸造台。

默认保留原残墙、落砖和废木料，工作台不开放锻造。修复时补齐四处缺失墙片，移除破碎构件与废料，摆放整齐的铁料，隐藏“待修复”牌，并以 `casting_station` 启用现有锻造界面和流程。

固定场景工作台通过 `AVoxelBuildWorld::SceneStations` 注册，复用现有锻造距离、占用、材料事务和联网入口。它不加入玩家建造 `Prefabs` 清单，不作为玩家建筑重复保存。首次加载等待丘陵及建筑世界准备完成，子关卡卸载时注销。

任务完成端调用 `ATemperateHillsWorld::CompleteVillageBlacksmithRepair(FText& FailureReason)`；建议任务标识 `hills.village.restore_blacksmith`。仅权威端可完成，室内有人或动物时暂缓；先成功保存，再切换碰撞、外观与工作台状态。修复布尔量复制到客户端，并保存在丘陵存档 V6 中。旧存档缺省为残破。围墙修复与地形保存均保留该状态。

本次提供修复状态和任务完成入口，未新增任务目标、消耗、NPC、奖励或临时修复按钮。

## 制作入口与交付边界

- `Tools/WorldGeneration/VillageBlacksmith/prepare_layout.py`：布局与生产用道路遮罩。
- `author_furniture.py`、`author_labels.py`：后台 Blender 家具模型、实体牌面纹理。
- `Run-Author.ps1 -Script author_install.py -Stage author`：使用 UE 批次互斥进行无界面导入、材质更新、子关卡保存。
- `save_layout.py`：仅重新保存布局，复用已导入资产。
- 制作回执：`SourceAssets/HillsVillageBlacksmith20261117/`；关卡回执：`SourceAssets/TemperateHillsVillage/Blacksmith20261117/author-saved.json`。

仅进行制作、必要编译、导入和保存；未运行游戏、视觉预览、截图或玩法测试。最终画面、行走和任务调用由用户测试。

2026-11-17 补存完成：用户退出运行后，使用独立、无游戏模块的无界面材质宿主完成实例化用途设置保存。橡木、锻铁、亚麻布和两块标牌共 5 个材质已保存；石材父材质原有设置已满足要求。资产保存回执为 `SourceAssets/HillsVillageBlacksmith20261117/furniture-usage-saved.json`，commandlet 日志报告成功、0 个错误。未追加运行测试。
