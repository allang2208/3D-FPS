# 温带丘陵异步入场与密林制作记录

## 主线可以直接使用的部分

传送门在无法取得异步预读句柄时会继续处理旅行。丘陵进入时显式建立自己的加载状态，联网来宾持有输入直到自己的丘陵准备完成。返回时环境句柄能保留未被下一批替换的资源。

主线原有地形流送器保留其数据结构和八个资产批次。附近地形等待半径改为 32 m，树木和岩石的 PCG 等待半径为 16 m，网格尺寸从实际 PCG 图读取。快速档略过远景和显示样本预热，只检查本批加载网格的编译状态；完整档会准备显示样本。两档都保留地面着色器和纹理检查。灌木和地面层在释放输入后分批激活。主线旧地形仍先准备初始 3×3 出生格。本机新版进一步按实际相交的出生格调度，优先异步读取实体植被，将装饰批次延后。

## 恢复本机新版丘陵

1. 从本次发布版本开始。先按[资产恢复说明](../../AssetSetup.md)安装有授权的资源，对照[回读清单](asset-registry.json)恢复本机 Content 中的路径。PCG 图、关卡、材质实例、第三方网格和纹理保留在本机。
2. [前置条件及逐文件散列](integration-prerequisites.json)列出新版丘陵所需的采集、天气、UE DynamicWind 和水体依赖。共享工程中需先核对现有实现。制作脚本使用的本地批次路径与输入见[密林地表](../../WorldGeneration/hills-rainforest-floor-20261111.md)、[生态配置](../../WorldGeneration/temperate-ecology-config-20261111.md)和[树木采集与矿脉](../../WorldGeneration/beech-harvest-ore-fix-20261110.md)。
3. 在干净的目标版本运行下面两条命令。第一条检查补丁与目标源码是否匹配；成功后第二条才写入工作区。最新本机工程已包含这些改动。

~~~powershell
git apply --check Docs/Publication/HillsAsyncEntry20261112/Integration/temperate-forest.patch
git apply Docs/Publication/HillsAsyncEntry20261112/Integration/temperate-forest.patch
~~~

补丁覆盖新版丘陵的地形与碰撞调度、迟加入的出生格保留、基于实际异步句柄的完整档资源收集、森林树种及地被分层、矿脉避让、湿地浅水和风动接入。程序化生成仍使用现有 PCG。配套作者脚本位于 Tools/WorldGeneration 和 SourceAssets 下对应的制作批次。公共源码与本机完整制作工程的差异记录在前置条件清单中。

## 归档与验证

[废案清单](retired-files.json)逐件记录原路径、归档路径、字节数、SHA-256、退役原因与现行替代文件。原制作记录中提到的旧 Backups 路径可用此表定位。旧快照保留在本机 trash/hills-async-entry-20261112，公共仓库只保存清单。原始授权素材、现行工程资源、作者输入和编译回执继续保留。

11 月 12 日本机完整工程的 Game 和 Editor Development 构建记录均为成功。已有资产登记回读包含 131 个包、4 张 PCG 图，未报告缺失包；灌木图同时承载第 2、4 层，草丛为第 3 层。发布时在单独的 Git 索引上应用恢复补丁，逐件核对目标源码散列。未在公共源码快照上重新构建，未运行游戏、联机回归或测量优化后的入场秒数。
