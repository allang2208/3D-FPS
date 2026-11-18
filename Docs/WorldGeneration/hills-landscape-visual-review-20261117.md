# 丘陵生成结果截图检查（2026-11-17）

用户本轮明确要求自行截图检查。已从同一个正式世界存档的副本启动隔离运行实例，保存并逐张查看 8 张 1920×1080 原始游戏截图。**当前画面不判为通过。**

## 运行与证据

- 世界种子：`1518277816`；生成版本：`3`。
- 世界身份：`DD5554E24E2BF263C186319F8C752D2E`。
- 村庄原点：`(337.474, -25432.532, 6142.0)` cm。
- 湖泊中心：`(-35812.625, -18558.687, 4128.617)` cm。
- 采石场中心：`(-27010.903, -39807.915, 6702.0)` cm。
- 隔离运行目录：`D:/FPS3D/FPSGAME/trash/hills-scenery-20261118/Saved/HillsLandscapeCapture20261117/20261117-205454`。
- 本轮只在隔离实例使用晴天上午光照、隐藏玩家和自由取景；正式存档前后 SHA256 相同，实例已正常退出（exit code 0）。
- [运行回执](D:/FPS3D/FPSGAME/trash/hills-scenery-20261118/Saved/HillsLandscapeCapture20261117/20261117-205454/exit.json)、[相机及采集记录](D:/FPS3D/FPSGAME/trash/hills-scenery-20261118/Saved/HillsLandscapeCapture20261117/20261117-205454/Evidence/result.json)、[可复用机位](D:/FPS3D/FPSGAME/trash/hills-scenery-20261118/Saved/HillsLandscapeCapture20261117/20261117-205454/Evidence/cameras.json)。

## 逐图结论

| 机位 | 观察 | 结论边界 |
|---|---|---|
| [01 湖泊俯视](D:/FPS3D/FPSGAME/trash/hills-scenery-20261118/Saved/HillsLandscapeCapture20261117/20261117-205454/Evidence/01_lake_overview.png) | 河道接入大湖；湖缘已有凹凸，但连续裸岸环带很强，局部出现黑色尖缝。 | 远景尚在加载，不能用这张判断最终远处树木密度或地表清晰度。 |
| [02 湖湾近景](D:/FPS3D/FPSGAME/trash/hills-scenery-20261118/Saved/HillsLandscapeCapture20261117/20261117-205454/Evidence/02_lake_cove.png) | 近处水面、湿岸、草和石块可见；对面岸坡存在大块陡直土墙及大片暗面，缺少自然坡脚过渡。 | 湖岸自然度未通过；暗面究竟来自坡型、法线、阴影或远近网格交接，未单独确定。 |
| [03 岬角坡顶](D:/FPS3D/FPSGAME/trash/hills-scenery-20261118/Saved/HillsLandscapeCapture20261117/20261117-205454/Evidence/03_lake_headland.png) | 近处树干、草、草本及蘑菇可见，树干底部在画面中接地；坡顶到水面高度差明显。 | 此机位没有覆盖陡岸侧面，不能据此判定整个岬角接地和坡面都正常。 |
| [04 河口](D:/FPS3D/FPSGAME/trash/hills-scenery-20261118/Saved/HillsLandscapeCapture20261117/20261117-205454/Evidence/04_river_mouth.png) | 水道可见并接入湖面；岸边有折线状地表黑缝和阶差，滩地仍很单一。 | 河口连续性和岸线细节未通过。 |
| [05 树簇远景](D:/FPS3D/FPSGAME/trash/hills-scenery-20261118/Saved/HillsLandscapeCapture20261117/20261117-205454/Evidence/05_tree_groves.png) | 高位机位没有得到可用于评价树簇的完整植被画面，远处背景也未就绪。 | **取景/加载条件不足，不据此宣布树簇算法无效，也不判通过。** |
| [06 林下近景](D:/FPS3D/FPSGAME/trash/hills-scenery-20261118/Saved/HillsLandscapeCapture20261117/20261117-205454/Evidence/06_forest_floor.png) | 可见树干周围灌木、蕨类和草的组合；画面中绿色草覆盖仍较连续，小枝石块的层次不突出。远处出现边界空隙。 | 近景组合已出现；枝条/碎石多样性和整体树簇形态未得到充分证明。远处空隙需在完整背景加载后复拍。 |
| [07 白崖/采石场](D:/FPS3D/FPSGAME/trash/hills-scenery-20261118/Saved/HillsLandscapeCapture20261117/20261117-205454/Evidence/07_white_cliffs_quarry.png) | 棚屋、部分岩块在画面中悬空；地表有黑缝、孤立薄片；石柱偏暗，采石场大面积裸坡。 | **未通过，优先复核物件落地高度与实际可见地表的一致性、地形网格交接。** 不能仅凭截图区分放置偏差和地表尚未完成细化。 |
| [08 进村道路](D:/FPS3D/FPSGAME/trash/hills-scenery-20261118/Saved/HillsLandscapeCapture20261117/20261117-205454/Evidence/08_village_approach.png) | 道路进入村门时与周围地面相衔接，本机位没有看到单独抬起的窄路堤；村庄建筑可见。 | 本角度视觉衔接可接受，未执行行走、碰撞或完整路线测试。 |

## 必须保留的加载限制

采集器在每个机位等待了约 31–56 秒，附近静态实例数连续至少 5 秒稳定后截图。这不等于所有地形细化、蒙皮树或远景资产都已就绪。

日志中完整资产批次 `ready_batch=3 completed=4/4` 和 `HILLS_BACKDROP canopy=225` 到 **21:04:25** 才出现；前六张早于该时刻，采石场图在其后约 3 秒，村庄图在其后约 61 秒。因此，前六张远景和地图边缘只作为问题线索；不能将缺树、远处空隙直接归因于最终生成算法。地面近景已经显示的坡型、环带感和材质层次可以作为下一轮修改参考。

下一次复查应等待完整背景与目标地块细化完成，额外使用贴近目标的地面 PCG 生成源，再从相同机位对比。特别是树簇要同时取地面和低空两组视角。

## 下一轮处理顺序

1. 对齐详细地形、远景代理和物件放置使用的高度；处理河口/采石场黑缝与悬空，再复拍相同机位。
2. 调整湖岸坡型：把连续陡直土墙拆成有长短变化的缓坡、局部岩岸、崩积坡脚和入湖浅滩，打断整圈裸岸。
3. 在完整加载条件下核对树簇轮廓和林间空地，再调整林下草的连续覆盖及枝条、碎石、蕨类的组合。近景已有组合，但尚不能算完成。

本轮未修改生产地形、资产或正式存档，也未把以上问题标记为已修复。

## 采集工具与构建状态

- 新增专用原生入口 `fps.Test.HillsLandscapeCapture`，要求 `-HillsLandscapeCapture` 显式参数，不影响普通启动。
- 启动脚本：`Tools/WorldGeneration/Start-HillsLandscapeCapture.ps1`；已编译模块的隔离光照适配：`Tools/WorldGeneration/hills_capture_daylight.py`。
- `HillsLandscapeCapture20261117R2` 的 Editor/Game 构建成功，以上截图使用该版本模块副本，包含本轮之前已完成的湖岸地形和植被改动。
- 首次采集 `20261117-204445` 的光照设置顺序和部分机位不适合评价，原始图片保留，不用于最终画面判断。
- 辅助代码后续修正的 `R3` 构建被共享源码 `WorldGeneration/HillsBlacksmith.cpp:45–52` 对 `ABronzeTorch` protected 成员的访问错误阻塞。未改动该文件，也未发送跨任务协调消息；没有宣称辅助代码最新修订已编译。第二次截图通过 R2 模块、固定机位 JSON 与隔离 Python 光照适配完成。


2026-11-18 整理：本页历史截图、旧宿主和过期备份已移入 trash；当前路径与散列见 [归档发布记录](../Publication/HillsScenery20261118/README.md)。后续状态以 [待办](hills-scenery-todo-20261118.md) 和 [最新完成记录](hills-closure-20261118.md) 为准，不将历史缺口重复记为当前通过。
