# 地牢可见地板穿落：碰撞启用修复

日期：2026-09-23。

用户反馈发生在普通房间内或刚跨过房门：几何可见，但角色向地下坠落。既有游戏日志记录该局种子 2064575536，布局已经报告完成。本轮没有重放该种子或启动游戏。

## 代码原因

`OwnGenerated` 在组件配置与注册前执行 `SetActorEnableCollision(false)`。UE 5.8 的组件注册可以因此跳过物理状态创建；实例化网格也有相同条件。

原 `FinishAssembly` 仅执行 `SetActorEnableCollision(true)`。引擎的 `OnActorEnableCollisionChanged` 更新已有碰撞体的过滤条件，不会创建未生成的物理状态。渲染与物理状态分别创建，因而可能出现网格可见、地板没有碰撞的情况。

## 修复

- 在提交布局时，启用 Actor 碰撞后遍历其已注册且应参与碰撞的 Primitive 组件。
- 对缺失的物理状态调用 `CreatePhysicsState(false)`，不延迟到恢复玩家移动之后。
- 已在异步创建的组件等待完成；无法创建时进入现有失败回退流程，不报告 Ready。
- 旧房间的销毁移至新碰撞就绪之后，保证失败时仍能保留旧布局。新房间随后显示，原有导航准备完成后才恢复玩家移动。
- 液体和其他 NoCollision 装饰保持原有设置。
- 生成指标新增 `physics_states_created_at_commit`，记录本次提交补建的组件数量。

改动位于 `Source/FPSGAME/Dungeons/AuthoredDungeonGenerator.cpp`，不改变房间池、地下 Boss 布局或模型。

## 交付状态

Editor 目标已后台常规编译、链接到基础 DLL。日志：`Saved/BuildEditor/build-20260923-181820.log`，结果 `Succeeded`。

未启动编辑器、PIE、自动化测试或渲染验收。运行效果由用户重新进入地牢后确认；编译成功不等同于游戏验证通过。

## 同日后续：分阶段加载

用户随后提出集中创建碰撞可能造成卡顿。后续实现将上述物理状态创建移入 `PumpAssembly` 的逐帧队列，结构优先，每个 Actor 配置完成后完成其碰撞；不再在提交时一次性遍历整座地牢创建。旧布局退场和新布局显示也分帧执行，玩家仍等全部准备完成后才恢复移动。指标改为 `physics_states_created_during_assembly`，加载方案见 [地牢分阶段进入](../UI/dungeon-staged-loading-plan-20260923.md)。上面的编译日志仅对应此前碰撞修复，后续构建状态以新方案记录为准。
