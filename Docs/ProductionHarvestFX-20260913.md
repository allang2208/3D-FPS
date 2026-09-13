# 采集效果与落地材料优化

本轮替换 [采集初版](ProductionTools-20260913.md) 中“木材、矿物直接进背包”的规则。保留 `6 / 7 / 8` 工具切换、三次命中、3.2 米使用距离、`F7` 返回武器及原有存档。

## 现在的表现

- 树木：第三次命中后移除原树及树干碰撞，复用原树模型倒伏；按丘陵高度采样调整停止倾倒的角度。接入木材破坏粒子和短时落叶，落地再触发一组扬尘。约 2.8 秒后分批释放四段可拾取木材，每段木材 ×1。
- 岩石：第三次命中后移除原岩块，接入破碎扬尘及六个预制碎块。普通岩块留下一份石材 ×3；含矿岩块留下石材 ×1 和对应矿石 ×2 两份掉落。
- 准星对准材料，在 2.5 米内按 `E` 拾取，沿用正式背包、仓库与已有物品数量。背包满时允许砍倒、采碎，拾取失败会把产物保留在地面。
- 可拾取物拥有实际原木／岩石模型、简单碰撞、重力与现有拾取提示／稀有度光效。落地后关闭持续物理模拟，物品保留。土壤仍直接进入背包，满包时不采集，不挖空地形。

## 使用的现有素材

| 用途 | 本地资源 |
|---|---|
| 木材破坏粒子 | `/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Destruction/P_Destruction_Wood` |
| 岩石破碎扬尘 | `/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Destruction/P_Destruction_Concrete` |
| 短时装饰碎块 | `/Game/Realistic_Starter_VFX_Pack_Vol2/Mesh/SM_Derbis_B` |
| 落叶 | `/Game/RuralAustralia/Effects/FallingLeaves/FX_FallingLeaves` |
| 木材掉落 | `/Game/RuralAustralia/StaticMeshes/Vegetation/Log_S_01/SM_Log_S_01`，缩放至约 85 厘米长 |
| 石材／矿石掉落 | `/Game/RuralAustralia/StaticMeshes/Rocks/Rock_S_02/SM_Rock_S_02`，缩放至约 24 厘米 |

复用原素材及其依赖，没有修改供应商资源。本次未生成新模型、纹理或握持动画。岩石采用预制碎块模拟破碎外观，没有实时切割原岩网格，也没有在整个 PCG 世界启用 Chaos。原木是现成倒木模型，不是从黑杨网格实时切割的匹配木段；矿石暂共用岩石外观，通过拾取名称区分类型。

参考旧 Godot `scripts/tools/tree_felling.gd` 的 2.4 秒加速倒伏、地形采样停止角、四段原木和 `E` 拾取规则，以及 `ore_break_fx.gd` 区分装饰碎屑与正式产物的做法。UE 本轮沿用初版 2.8 秒倒伏时长，未迁移 Godot 的运行时树干切面与岩石预切模型。

## 保存与流送

第三次命中的同一次 ColdSteel A/B 档案提交中，写入资源采尽状态和所有地面物品记录。保存失败时不移除原资源；成功后才播放效果。木材掉落等待只影响当前场景中的显示，重新读档时无需重播倒树，未领取产物按记录恢复。

新增可选字段 `FColdSteelItem::HarvestWorldId`，将地面材料绑定到对应随机丘陵世界 GUID，避免同一地图不同种子串出旧材料。进入背包／仓库后清除该字段，保持普通材料堆叠规则；在丘陵手动丢弃这些材料时重新绑定当前世界。旧档案缺少字段时沿用原来行为；此前已经直接收入背包的采集不会补发额外掉落。

普通背包丢物仍沿用原有刷新流程，带世界 GUID 的采集物由 `UProductionHarvestSubsystem` 独立控制可见范围。流送卸载前缓存物件实际位置、旋转，沿用原来的自动保存及离开场景保存，不通过装饰特效 Actor 保存奖励。

## 性能预算

- 装备斧／镐时异步准备对应掉落模型、效果及拾取光效；世界级句柄保留已加载资源。第三次命中若掉落模型尚未就绪，保留资源和两次命中进度，并提示稍后挥动。
- 只显示玩家 64 米内最近的最多 40 份采集物；每 0.2 秒最多创建一份、卸载两份。远处保留存档记录，不保留可见 Actor。
- 最多同时两组破坏效果，每次岩石破坏六个装饰刚体，合计不超过十二个。这里的数量限制不包含供应商粒子系统内部的粒子。
- 装饰碎块只碰撞静态地形，不参与采集、不推挤玩家；1.4 秒停止物理，随后缩小，2.4 秒回收整个效果 Actor。木叶约 0.35 秒停止继续发射，破坏粒子约 0.7 秒停止继续发射，随效果 Actor 清理。
- 可拾取材料的物理模拟最多两秒，然后保留查询碰撞，提示更新频率降为约 6.7 次／秒。远离玩家只卸载外观，不删除奖励。
- 砍树／采矿直接移除命中的 ISM／实例化骨骼树实例，不再每次重新生成整个 PCG 单元。后续流送继续依赖原有稳定候选 ID 过滤采尽资源。

这些是代码中的预算与实现策略，不是实测帧率或最大卡顿数据。

## 交付记录

源文件主要位于 `Source/FPSGAME/Production/ProductionHarvest*`、`ProductionBreakEffect*`、`UI/ColdSteelProductionDrops.cpp`、`UI/ColdSteelPickupMaterial.cpp`。素材目录已补入 `DefaultGame.ini` 的烹饪列表；Fab 二进制资源不公开提交。

本机工作树必要构建均成功：`FPSGAMEEditor Win64 Development`（模块后缀 `913972`）及 `FPSGAME Win64 Development`。日志位于 `Saved/ProductionHarvestFX/build-editor-final.log` 和 `build-game.log`。首轮构建修正了局部变量名称遮蔽及 `TObjectPtr` 数组遍历的编译错误。

依用户规则未启动游戏、PIE、性能测试、渲染或截图验收；重启 UE 编辑器后由用户测试效果与手感。
