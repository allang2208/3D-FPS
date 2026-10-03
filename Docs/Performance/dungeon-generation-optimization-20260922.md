# 地牢生成与常驻开销优化

宿主：UE 5.8.2 / FPSGAME / `L_Dungeon_Randomized`。继续使用 `Dungeons/AuthoredDungeonGenerator` 和地图中实际安装的目录，包含宝藏侧室与扩展房型。不启用旧 Dungeon 生成器。

## 源码实现

- 游戏内布局搜索移到工作线程，只处理目录 JSON、随机流、变换和包围盒。取消或离开地图后，过期结果不会应用到新一轮生成。编辑器预览仍同步完成，兼容现有安装脚本。
- 旧预览销毁、唯一资源解析、每件网格与碰撞注册、宝箱、灯光、定位点均进入有时间预算的主线程队列。默认 `fps.Dungeon.Generation.BudgetMs=3`；最少执行一个任务，因此大型资源加载/组件注册仍可能超过预算，记录真实最慢批次。
- 成功取得完整布局才替换旧布局。构建期间保留加载页并暂停原本启用的角色移动组件，碰撞就绪后恢复。缺资源时不把有洞的半成品报告为成功，加载页保留返回入口。
- `fps.Dungeon.Instancing=1` 在下一次生成时把重复的兼容刚性网格聚合为 ISM，按 40 m 空间单元、网格、材质、碰撞、阴影设置分组。只有有效 Nanite 数据的非流体网格进入此路径；保留非 Nanite 的独立组件以免改变 Lumen 支持范围。组件标签保留所含模块，交互宝箱与危害区域独立。
- 积液按玩家控制器直接枚举目标，去掉每区的 OverlapMulti 和临时接触列表。仍使用独立脉冲时钟及原伤害、湿区形状、脚底高度和接地判断；生成完成后才启用伤害计时。
- 启动日志出现每组件约 30 万至 52 万三角形的导航碰撞导出警告。覆盖在壳体上的 `_Tiles` 装饰网格与 `_Fixtures` 不再影响导航，底层 Shell、地面、桥面继续参与；瓷砖物理碰撞/弹道查询不变。目录可用 `affects_navigation` 覆盖，实例组同时按该设置分开。
- 宝箱闭合动作求值一次后关闭骨骼 Tick。未来开箱逻辑需先 `SetComponentTickEnabled(true)`，再播放动作；当前 FutureTreasureLoot 语义不变。

## 资产接入脚本

`SourceAssets/DungeonPerformance20260922/Scripts/optimize_assets.py` 每批至多保存 8 个刚性网格，以当前编辑器里生成器的目录为准，不使用旧 66 模块统计作为现状。

- 两个 Routes 粘液父材质的法线改用解析导数，替换每像素四次形状求值的有限差分。保留 WPO、局部坐标到世界坐标转换、透明度、颜色、粗糙度与灯光模式。原法线代码写入 Receipts，可供恢复；不降低近景透明质量。
- 仅处理所有实际使用材质均兼容的刚性网格。启用 Nanite 并保留显式切线、100% fallback 三角形与既有碰撞。跳过流体、透明或不支持的材质。重导入脚本保留已设的 Nanite 选项。
- **本轮不把复杂门洞、破口、桥面或管线强行替换为单个简化碰撞体。** 碰撞资产本身保持原样；本轮减少危害查询和集中注册的开销。若后续修改碰撞形状，需从各房型源几何逐件构造，不能用房间外包围盒替代。
- 修改成功逐项写入 `Receipts/assets.json`。未接入与已保存数量分开报告；脚本在试玩或已有未保存目标资产时停止，避免覆盖现场。

## 面板与数据

schema 8 的 `dungeon_generation` 独立记录本次生成的种子、状态、模块/宝藏房数、阶段 CPU 时间、创建批次数、最慢批次、资源解析数与实例化数量，不受网格 Top N 截断。规划未完成时不读取工作线程仍在写入的数据。

共享生成器后续加入的暂存/提交、失败回退与按目录要求准备导航均予以保留；`Dungeon.Finalize` 单独记录提交及导航准备的主线程时间，不把它混入创建批次的 3 ms 预算。最慢创建批次不代表整帧峰值。

环境正文显示生成摘要，卡顿事件显示各阶段中文名称。创建批次包含其子阶段，不能再与子阶段相加；网格与碰撞注册尚未单独拆分为物理 cooking 时间。未采集 GPU 阶段时继续使用 null，不根据实例数或预算推算帧数收益。

本轮不运行游戏测试、截图、自动检查或回归，实际效果由用户测试。必要的编译、资源构建与保存分别在构建日志和资产 receipt 中记录。

## 已保存资产

- `SourceAssets/DungeonPerformance20260922/Receipts/assets.json`：2 个 Routes 粘液父材质、79 个当前已安装目录的刚性网格已保存，待处理数 0。这个数量不包含未来追加的房型资产；新房型通过同一脚本按其实际目录补充。
- `SourceAssets/DungeonPerformance20260922/Receipts/preview-navigation.json`：`L_Dungeon_Randomized` 中 70 个现有生成装饰组件已关闭导航影响并保存，未重新生成布局，物理碰撞不变。
- `SourceAssets/DungeonPerformance20260922/Receipts/close-editor-final.txt`：按用户授权保存并发出正常编辑器退出请求；后续基础 DLL 更新使用常规 Editor 构建，不运行 PIE。
- 完整构建遇到 Unity 合并编译名称冲突，`FPSPlayerBodyActions.cpp` 的火球组件局部变量由 `Magic` 改为 `FireballMagic`，避免遮蔽体素存档常量；未改变动作逻辑。
- 2026-09-23 的完整构建已编译地牢生成、灯光、积液和性能面板模块，但被 `WitchProjectile.cpp` 的随机流初始化语法阻塞。将 `FRandomStream CosmeticRandom(int32(GetUniqueID()));` 改为花括号初始化，消除函数声明歧义，保留原随机种子与用途。

## 最终构建交付（2026-09-23）

- `FPSGAMEEditor Win64 Development` 常规目标构建成功，已链接写入基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll`，并写入目标元数据。最终增量构建完成 13 个步骤，用时 14.26 秒。
- 构建日志：`Saved/PerformanceDiagnosis20260922/build-dungeon-generation-full-6.log`，结果 `Succeeded`，退出码 0。前次构建期间出现的 PKM 头文件与调用处不同步，在重新读取当前源码后消失；本任务未修改其换弹逻辑。
- 保存及正常退出记录：`SourceAssets/DungeonPerformance20260922/Receipts/close-editor-build6-20260923.txt`。未强制结束编辑器，未为验收重新启动 UE。
- 本轮只完成必要编译与资产接入，未运行游戏、性能测试或回归；实际帧数、进入地牢的卡顿及画面效果由用户测试。
