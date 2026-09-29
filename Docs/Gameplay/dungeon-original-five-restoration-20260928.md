# 原五间房恢复与派生配置退役

日期：2026-09-28。

用户要求先把 30 个普通房间配置调整回原五种，再设计五种完全不同的废弃设施，减少近似变化和代码冗余。新五间仍处于方案阶段。

## 实际保存

- 普通房池：Distribution / Drainage / ShoredBreach / VentilationLoop / FreightTransfer，共五种原始完整模块。
- 有效目录移除 40 个派生模块：30 个尺寸档、4 个桥位/机组偏移、6 个通风壳/内装组合；删除其共享库及专用版本标记。
- 保留岔路、连接件、宝箱、楼梯、Boss、奖励、刷怪池、墙面/材质、灯光及性能改进。
- 移除随机维修桌台的四处设备布置及对应避让区，重新生成设施配方；同步移除作者函数、导出条目和导入清单。其他八种设施组合件仍保留。
- 生成器解除退役尺寸/偏移网格及维修桌台的 282 个硬引用。旧网格资产暂保留本机文件，不再由当前目录加载；没有在已有编辑器运行期间移动可能加载中的 Content 资产。
- 保存到 `/Game/__ExternalActors__/GameMaps/L_Dungeon_Randomized/8/N2/KZ839Z5RGFD4Y0908097LH`；未覆盖根地图。作者目录 `SourceAssets/DungeonRoutes20260922/Config/catalog.json` 同步更新，generator_version=7。
- 后台 commandlet 正常退出，保存回执：`Saved/DungeonOriginalFive20260928/install.json`。

## 源码收拢

- RouteRepairs 取消 RoomVariants 和 RoomSizes 自动叠加。
- Composition 仅保留三岔封板和任务路由，不再生成通风壳/内装库或改写房间池；作者配置与安装脚本同步简化。
- 移除共享房间展开解析器及两个调用点、尺寸备用池、尺寸清单字段、外围装饰坐标重映射、桥宽/机组偏移装饰适配、相同房壳派生去重和 Spawn 的内部配方同步。
- 保留房型重复代价、合法端口与路线搜索、表面材质变化，以及独立随机设施场景功能。
- 退役的 RoomVariants / RoomSizes 作者目录及 AuthoredDungeonCatalog.cpp/.h 移到 `trash/dungeon-room-variants-retired-20260928/`；345 个源文件的原路径、大小、SHA-256 见 `retired-source-manifest.json`。编辑前源码另存 `BeforeEdits`。
- 单次目录迁移脚本：`Tools/Dungeons/restore_original_five_20260928.py`，不作为后续扩展层反复叠加。

## 构建与未测边界

此前 Editor 当前会话 Live Coding 成功，输出在 `Saved/DungeonOriginalFive20260928/livecoding-result.txt`。Game Development 目标后台构建成功（退出码 0），二进制已落盘；日志为 `Saved/DungeonOriginalFive20260928/build-game.log`。

用户随后关闭 UE，已补齐完整 Editor 构建收尾。等待既有构建结束后，执行 `FPSGAMEEditor Win64 Development -NoHotReloadFromIDE`，UBT 返回 `Target is up to date`、`Result: Succeeded`（退出码 0）；当前完整 Editor 目标已包含最新源码，不再处于仅热补丁完成的状态。日志为 `Saved/DungeonOriginalFive20260928/build-editor-full.log`。没有重新打开 UE 或运行测试。

未启动交互编辑器、游戏、PIE、种子回归、截图或渲染；构建和资产保存不等于运行效果已验收，由用户自行测试。地图配置已落盘，下次由用户打开地图时读取新目录。

## 下一阶段方案

后续用户授权自查已完成，发现并清理了刷怪作者配置中的四个旧派生房型，修复五房池闭合搜索；后台 5 个种子共 6 次规划与独立结构核对通过。详见 [冲突与遗漏复查](dungeon-review-20260928.md)。上节“不主动测试”是原恢复阶段记录，不能代替本次结果；视觉与实际游玩仍未验收。

见 [五种独立废弃设施方案](dungeon-five-new-templates-proposal-20260928.md)：地下车站、隔离病区、枯死培育温室、数据档案中心、焚化处理厅。每房一套完整结构，最终十个独立普通配置；不再派生三档尺寸或共享壳/内装排列。
