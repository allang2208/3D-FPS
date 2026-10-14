# 龙息联机修复 · 2026-10-14

用户授权全面修复上一轮龙息检查发现的五项问题。范围为龙息与必要的公共施法、断线和换图接入；不改其他魔法数值、当前暖色体积资产或全项目联机架构。

## 请求与预测

- `FColdSteelNetCastRequest.CastId` 对龙息取本次 Prepare 的请求序号，Release 和 Stop 保留同一个编号。
- Phase 0 Prepare、Phase 1 Release、Phase 4 Stop/Cancel 均通过所属 PlayerState 的同一个 Reliable RPC。移除原角色组件上的独立停止 RPC。
- 服务端保存待释放龙息编号；释放必须匹配预留，停止只取消同编号预留或结束同编号活动龙息。重复或迟到的旧停止请求不会结束后续施法。
- 龙息回执携带 CastId，先校验 Pawn，再交给技能按编号处理；不再被另一种魔法更新后的全局请求序号丢弃。
- 客机预测状态与服务器复制状态分开。取消立即清除等待标记并记录已取消编号；迟到的激活复制不会重建已经取消的火焰。服务器确认可结清该次蓝耗，但不拿走后来其他火系技能的手势付款记录。
- 本次请求/复制结构属于网络协议变化，主机与客机须使用同一版本构建。

## 喷口与声音

- 释放接触点读取已有法杖尖，将其换算成相对 Pawn 眼部、随瞄准旋转的偏移。服务器校验有限值与物理长度范围后，将偏移包含在本次复制状态中。
- 服务端伤害、本机预测和旁观者体积喷口都使用这份偏移，不再为远端使用角色中心 +35/+55 的另一套位置。移动和转向仍跟随 Pawn；眼部到喷口的阻挡检查继续保留。
- 偏移在释放时锁定；不会为每帧手腕细微晃动增加可靠 RPC 或更改第三人称动画资产。第三人称动作继续沿已有角色表现同步。
- 施法音从各端的龙息状态入口播放，每次 CastId 最多一次。本机预测与确认使用同一编号去重；晚进入相关范围时不补播超过 1.25 秒的旧起手音。专用服不播放声音或创建火焰组件。

## 修炼与生命周期

- 服务端开始龙息时记住本次施法的权威模型，避免收尾时因控制器解绑而误用本机档案。
- 断线保存、组队换图保存之前，先结束活动龙息并结算已经确认的命中修炼。
- 组件 EndPlay 增加幂等收尾作为销毁路径的补充；活动标记和清空累计奖励阻止重复结算。
- 未喷出的预留仍退款；喷出后的中断不退款。保留既有死亡修炼策略、6–8 秒持续时间、0.5 秒伤害间隔、90 度与 5–15 米范围成长。

## 文件与交付边界

主要实现：`Skills/FPSDragonBreath.cpp`、`FPSFireMagicComponent.*`、`FireMagicTypes.h`、`NetCastUtils.h`；公共接入：`Multiplayer/ColdSteelPlayerState.*`、`ColdSteelCampfireRequests.cpp`、`ColdSteelTeamTravel.cpp`，均位于 `Source/FPSGAME` 下。

必要构建记录放在 `Saved/DragonBreathNetwork20261014`。构建的最终状态以该目录回执和对应日志为准。

2026-10-14 最终构建结果：

- `FPSGAME Win64 Development`：退出码 0，`Result: Succeeded`，`Target is up to date`；记录为 `game-build-final.log`。
- `FPSGAMEEditor Win64 Development`：退出码 0，`Result: Succeeded`，`Target is up to date`；记录为 `editor-build-final.log`。
- 最终两次调用串行执行，使用 `-NoHotReloadFromIDE`。编译器确认当前源码对应的 Game 与 Editor 产物均为最新；没有重新启动 UE。
- 首轮 `game-build.log` 保留失败现场：构建期间怪物模块头文件更新，导致 UHT 生成行号不同步及新头文件尚未纳入该轮编译。未修改或回退怪物源码；等待共享构建结束、重新调用构建后已不再阻挡。

机器可读交付回执：`Saved/DragonBreathNetwork20261014/build-receipt.json`。

本轮按用户规则只完成开发与必要构建，不启动编辑器、游戏、主客机、延迟/丢包模拟或视觉/性能验收。源码处理了上述路径，不将编译成功视为实际联机验收。
