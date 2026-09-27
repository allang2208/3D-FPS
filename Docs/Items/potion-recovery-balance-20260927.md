# 药水恢复数值调整（2026-09-27）

用户确定：任何角色等级都可饮用所有品阶；全部药水使用固定值加对应资源最大值百分比，提升低阶药水的补给价值并保留品阶差异。

| 品阶 | 生命恢复 | 魔法恢复 |
| --- | --- | --- |
| 普通 | 30 + 最大生命值的 15% | 25 + 最大魔法值的 15% |
| 中级 | 80 + 最大生命值的 20% | 60 + 最大魔法值的 20% |
| 高级 | 150 + 最大生命值的 25% | 120 + 最大魔法值的 25% |
| 特级 | 180 + 最大生命值的 30% | 150 + 最大魔法值的 30% |

普通红药在最大生命 200 时恢复 60，普通蓝药在最大魔法 250 时恢复 62.5；两者在最大值 1000 时分别恢复 180 和 175。实际恢复受当前缺失量限制，按喝药接触结算时的最大值计算，满资源拒绝消耗。目录中的 level 仍为物品元数据，不加入角色等级使用门槛。

`Content/ColdSteelData/items.json` 的八种药水同步更新 useEffect、desc、stats。价格、掉落表与喝药动作时序未改动。

`Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp` 的 ReloadProfile 在现有目录同步阶段更新药水实例的 useEffect 和 stats。描述沿用已有目录同步；数量、实例 ID、位置和快捷栏绑定保持原值。仅发现差异时进入既有 A/B 存档提交。新生成药水直接复制更新后的目录；已有药水在下次成功读取并迁移档案时应用，未直接修改本机玩家存档文件。

配置和源码已落盘，未启动编辑器或游戏，未执行游戏测试。

后台 FPSGAMEEditor 构建未完成：`Saved/BuildEditor/build-20260927-102316.log` 返回 OtherCompilationError。错误位于弓模块：`BowFlexMeshComponent.cpp`、`BowPartComponent.cpp` 对 UPoseableMeshComponent 调用不存在的 GetSkeletalMeshAsset，以及 `BowWeaponComponent.cpp:797` 的 ApplyStringLoad 调用缺少第四个参数。本轮没有修改这些弓模块文件，也没有生成新的完整 DLL；旧药水的读档同步源码需工程成功构建后生效。没有直接迁移本机玩家存档。
