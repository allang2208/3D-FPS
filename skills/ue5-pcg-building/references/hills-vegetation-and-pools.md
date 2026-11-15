# 雨林植被与局部积水

适用于 FPSGAME 温带丘陵的绿色雨林地被、生态参数和浅水坑；不把其它生物群系或黄色草甸一起替换。

- 白模先沿实际 StaticMesh 材质槽、材质实例、父材质和贴图绑定定位；仅修改 tint 不代表材质链已经完整。RainforestCarpetGrass 的三种资产各有自己的 GrassRestBoundsMin/Max，重建脚本必须随保存资产同步。
- 用户已拒绝的粗草是 WetForest/Underfoot/SM_BankSedge。保持其退出活动草调色板和导入入口，不因“增加密度”重新加入。不要将旧草尺寸读回记录当作当前可恢复资产清单。
- 联机生成使用该世界房主下发的 NetEcology 快照和 SizeMeters；客机及晚加入等 Ready 后再开生成管线。地形工作线程捕获纯值/不可变计划，PCG、远景、地图和动物栖息地显式传递同一配置。不要改写进程全局 Get() 来“同步”客机；同进程可存在多个世界。
- 雨林扩大后，水坑候选边界应来自实际雨林 mask，不继续使用旧椭圆半径围绕 ForestAnchor 搜索。当前实现按 8 m 粗筛、适宜性加分散度选择最多六个 64 m 地块，局部 1 m 优先洪泛，最多八个浅水坑。计数是预算上限，不是每个种子的保底生成数。
- 选址使用未经玩家编辑的种子地形；挖填在塑形后计算，因此不会搬移选址，但可以排水或填平。候选边缘和积水网格均避让河岸与谷地道路，排除点作为泄水口，不能形成假水坝。
- 分块积水的 Pool.Cells 保留父计划的世界格坐标；高度采样、水面三角形、岸边湿度、接触和村庄避让须使用相同坐标合同。扩展搜索区域不等于扩大整个高分辨率洪泛网格。

入口：TemperateEcologyConfig、TemperateForestHabitat、TemperateHillsWorld、TemperateForestWater。2026-11-15 的 Editor 构建记录在 Docs/Publication/HillsVegetation20261115/Evidence；该轮未运行新的联机或水坑实机验收。
