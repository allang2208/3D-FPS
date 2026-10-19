# 法袍原地转向时膝部穿模：布料回写顺序修复

用户反馈：空手、第三人称、站在原地转动镜头时，膝部仍穿出法袍。预期是在保留自然转身、抬脚和完整小腿衔接的情况下，让内搭依据当前正在显示的裙摆收束。

## 源码定位

- `FPSBodyGrounding.cpp` 的原地转向会在身体与落脚朝向相差超过 35 度时启动换脚，单次约 0.48 秒，脚部最高抬升 7 cm。膝盖和骨盆因此发生实际姿态变化，不能仅按角色移动速度判定腿部静止。
- `UFPSModularOutfitComponent` 默认位于 `TG_PostUpdateWork`，旧逻辑在这里读取布料并写入腿部收束材质。
- 本机 UE 5.8 的默认异步布料在 `TG_LastDemotable` 执行 `ClothEndTickFunction`，由 `HandleExistingParallelClothSimulation()` 完成任务并调用 `WritebackClothingSimulationData()`，晚于旧收束更新。
- 当前引擎的 `GetCurrentClothingData_AnyThread()` 不会等待/回写。任务未完成时返回空表；任务完成但尚未回写时，仍可能得到上一份缓存。旧逻辑因而可能用旧裙摆或蒙皮回退包络约束当前膝盖，而渲染在帧末拿到新的裙摆。
- 材质坐标路径、当前衣物目录、转向腿部求解及材质覆盖已按此问题范围读取。本轮未捕获实际游戏帧，不能把源码顺序缺陷表述为已经复现并排除全部视觉原因。

## 修复

在创建有裙摆包络的外观时，给该角色的外观 Tick 增加三项显式前置：法袍姿态 Tick、布料 Tick、布料结束回写 Tick。UE 的依赖调度会让外观更新排在当前法袍回写之后，再向内搭材质提交同帧数据；没有手动 Wait/Flush，也没有 GPU 回读或遍历蒙皮网格。

释放外观时移除这三项依赖，避免换装后留下旧法袍的调度关系。正常异步模式由 ClothEndTick 保证，布料 Tick 内完成模式由 ClothTick 保证；停用的 Tick 不参与依赖。项目未覆盖引擎默认 `p.ClothPhysics.UseEndTickWait`。

更新位于共用身体显示路径，覆盖空手、枪、弓、法杖、双手锤及远端角色各自的法袍。保留原转身动作、IK、布料参数、完整小腿、现有兜帽修复与 32 条内搭资产引用。无需重新制作模型或导入资产。

## 交付状态

源码已修改并完成后台构建。`turn-hem-sync-build-01` 在构建前发现现有 UE 编辑器并退出保护；用户保存并关闭 UE 后，`turn-hem-sync-build-02-FPSGAMEEditor.txt` 返回 `Result: Succeeded`，构建用时 22.14 秒，已更新 Editor 游戏模块。此次不需更改/重新导入模型与材质资产。未启动游戏、未执行楼梯/转身画面或联机验收，用户仍需确认实际画面。
