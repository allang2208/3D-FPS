# 自动步枪持续射击被档案刷新中断

用户报告：全自动步枪按住左键持续射击时会意外停止。预期在有弹药且无合法动作中断时持续射击。

## 定位

源代码中存在以下确定的状态清空路径：

1. `UColdSteelStatusModel::TickRuntime` 每累计 5 秒调用 `SaveNow`。
2. `SaveNow → CommitState → ApplyToPawn → AFPSGAMECharacter::ApplyColdSteelProfile` 刷新角色与装备。
3. `ApplyColdSteelProfile` 调用 `UPistolDualWieldComponent::RefreshEquipment`，即使当前装备为步枪。
4. 步枪不满足双持条件，`Want=false`；旧条件 `if(!Want || Changed)` 总会调用 `CancelInputs`，将角色共享的 `bFireHeld` 清为 false。
5. `ServiceHeldFire` 看到 false 即返回。物理左键仍按住，没有新的按下边沿，因此不会自动恢复。

由于自动保存使用自己的累计时间，从开始射击到中断的间隔不固定；其他导致档案重新应用的操作也可能触发同一路径。射击循环的追帧上限只丢弃过多的补射事件，并不会清空按住输入；本次定位的故障位于未启用的双持组件越权取消输入。

## 修复

只修改 `PistolDualWieldComponent.cpp` 的装备刷新入口：当前未启用双持且新装备也不满足双持时直接返回，保留正在使用的单枪输入与表现。

真正进入双持、退出双持或更换双持组合仍走原取消流程；处于双持时的菜单、死亡与翻越中断也沿用原逻辑。没有改自动保存周期、射速、弹药、半自动单次按压规则或存档数据。

## 交付

正式模块构建完成：`Saved/BuildEditor/build-20260915-091854.log`，结果 `Succeeded`。构建曾被另一个怪物动画制作命令进程占用，等待其退出后使用工程正式构建脚本完成。

本轮为代码调用链排查和最小修复，未运行游戏复现、自动测试或实机验收。用户测试时可持续按住自动步枪跨过一次自动保存，并观察击杀后持续射击以及真实松开、切枪和开菜单时的正常停止。
