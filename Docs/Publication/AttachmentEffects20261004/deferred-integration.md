# M14 韧性接入的发布依赖

本次共享工作区的 `SpiralPillarM14.h/.cpp` 及相关动画/AI/特效源码未由其制作任务提交，不能把整套怪物混入改造效果提交。以下接入已在完整本机工作区存在，暂不写入缺少M14类的公开快照。

- `MonsterToughnessProfiles.cpp`：包含M14头文件，并在 `SpeciesOf` 识别 `ASpiralPillarM14` 为 `spiral_pillar_m14`。JSON中的精英600数值已保留。
- `MonsterCoreStats.cpp`：读取M14实例的品阶及基础属性；公共韧性配置仍复用该入口。
- `MonsterCombatComponent.cpp`：M14的生命、AI、受击表现和 `ApplyToughnessReaction` 路由；普通硬直、显式控制、归巢分别沿共享时钟处理。
- `MonsterMeleeKnockback.cpp` / `MonsterParryReaction.cpp`：M14打断路由使用已在本次发布的韧性/眩晕合同。击飞必须先经过 `CanReceiveLaunchOrKnockdown`。

后续发布M14时，保留上述当前工作区差异即可，不要把本次公开版本复制回本机覆盖。新增M25的接入与本任务无关，也保留在原工作区。
