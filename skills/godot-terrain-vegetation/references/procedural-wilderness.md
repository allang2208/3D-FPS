# 程序化旷野扩展接口

## 入口路径

- 世界公式：`scripts/wilderness_generation_profile.gd`
- 只读生成上下文：`scripts/wilderness_generation/generation_context.gd`
- 规则注册表：`scripts/wilderness_generation/rule_registry.gd`
- 树木规则：`scripts/wilderness_generation/rules/vegetation_rule.gd`
- 矿脉规则：`scripts/wilderness_generation/rules/deposit_rule.gd`
- 地标规则：`scripts/wilderness_generation/rules/landmark_rule.gd`
- 地形修改接口：`scripts/wilderness_generation/interfaces/terrain_modifier.gd`
- 散布生成接口：`scripts/wilderness_generation/interfaces/scatter_generator.gd`
- 地标生成接口：`scripts/wilderness_generation/interfaces/landmark_generator.gd`
- 区块数据生成：`scripts/wilderness_generation/chunk_generator.gd`
- 异步队列：`scripts/wilderness_generation/chunk_scheduler.gd`
- 近景分帧提交与卸载：`scripts/wilderness_generation/chunk_presenter.gd`
- 磁盘缓存：`scripts/wilderness_generation/chunk_cache.gd`
- 新游戏种子：`scripts/wilderness_generation/world_seed_store.gd`
- 默认规则目录：`assets/data/wilderness/rules/`

## 新增要素

新增树木：导入近景模型和中景 impostor，新建 `WildernessVegetationRule` `.tres`，填写生态区、高度、坡度、湿度、距水范围、密度、间距、LOD/碰撞距离及采集产物。规则文件放进默认目录后会自动注册。

树木/矿石的 `scene_paths` 必须指向纯表现资产场景：允许在 `_ready()` 中构建网格，但不得启动 AI、写存档或产生其他玩法副作用。需要玩法逻辑的节点由近景实体层根据稳定 `feature_id` 单独创建。

新增矿脉：新建 `WildernessDepositRule` `.tres`，填写允许地质、生态区、高度、坡度、矿脉阈值、间距、模型变体、产物与工具等级。不要把新矿种写进核心 `match`。

新增营地、遗迹或洞口：使用 `WildernessLandmarkRule`。普通地标只声明占地、净空、生态和距水条件；需要整平或改变地形时，另建 `WildernessTerrainModifier`，通过注册表按 `priority` 注册。

特殊散布算法可继承 `WildernessScatterGenerator`；跨区块大型结构可继承 `WildernessLandmarkGenerator`。生成阶段只能返回纯数据，不创建节点、资源或碰撞；实例化交给主线程表现层。

## 稳定性合同

- 随机结果只能依赖 `world_seed + 绝对世界坐标 + rule_id`，不能依赖加载顺序或全局 `randf()`。
- 新游戏创建新种子，读档复用旧种子。增加普通规则只影响尚未探索区块；修改基础高度或水文公式时提升生成器版本。
- 水系和大型地形修改先于地标、树木、矿脉与草。河床低于水面、干岸高于水面，区块共享边界采样。
- 后台线程仅计算 PackedArray 和候选字典；Terrain3D、SceneTree、MultiMesh、碰撞和资源实例化只能在主线程提交。
- 近景保留根部拟合、木质碰撞和采集身份；中景无碰撞并使用 LOD/impostor；远景只进入宏观贴图。

## 验证

运行 `tests/test_wilderness_generation_system.tscn`，检查种子生命周期、规则发现、跨次确定性、河湖高度合同、区块缓存往返及后台队列。接入真实表现后还要运行 `tests/test_scenic_valley.tscn` 并做固定机位渲染；无头退出码不能替代视觉验收。
