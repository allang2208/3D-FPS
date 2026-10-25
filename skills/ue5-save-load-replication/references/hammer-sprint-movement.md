# 战锤冲刺：可靠攻击与 CMC 移动的共同身份

用于已提交近战攻击驱动预测前踏或空中惯性的系统。这里的 100 cm、0.25 秒和容差是战锤案例值，不是通用反作弊阈值。检查夹具仅在用户要求排查时运行。

## 身份与顺序

- 攻击 RPC 负责服务器接受攻击、冻结武器实例／方向／时钟与一次扣费；CMC 移动包携带相同攻击编号。普通移动 Sequence 不能替代攻击身份。
- 专属 `HammerDash` / `HammerAirMomentum` 与剑、弯刀请求分开。服务端从已提交攻击返回阶段累计距离和总预算，不信客户端方向、速度或单帧增量。
- 移动包可能先于可靠攻击 RPC 到达。只等待尚未处理的攻击编号；已拒绝、已取消、过期和旧编号不能借下一次攻击恢复授权。重复攻击 RPC 不重复扣费，也不取消已接受的本次动作。
- 累计距离只应用尚未处理的差额。阶段时间限制阻止提前走完整段；接触之后关闭前踏窗口，不能把迟到位移留到下一次攻击。

## 空中与取消

- 远端冲刺准备读取 CMC 传来的奔跑意图，而非服务端不存在的本地 Shift 键。只有已经挣得的准备资格才能在空中／滑铲延续。
- 滑铲跳跃与攻击 RPC 可能乱序。先让 CMC 处理排队跳跃和当前压缩标志，再承接服务器已有水平速度；可靠 RPC 不提前 StopMovement 或 StopSlide 吞掉跳跃。
- 空中惯性使用服务器真实速度并保留重力、碰撞和落地，不叠加地面固定前踏。
- 取消、死亡、换武器、动作失效和迟到拒绝清理对应攻击的移动。SavedMove 回放不能恢复已拒绝惯性；旧取消不清理新攻击。单机／监听主机本地没有网络攻击编号时也要清理其惯性。
- 服务端准备与权威状态更新须位于本地视模为空的早退之前；无渲染服务器仍需执行逻辑。

## 检查入口与能证明的范围

- `WarhammerNetworkAudit -SprintOnly`：直接调用权威处理器，覆盖身份、重复／乱序／取消、距离、墙体、空中与序列化。2026-10-25 为 28 项通过；不是 UDP。
- `-RuneboundReviewWire -HammerSprintWire`：实际本机监听主机和客机、可靠组件 RPC 与 CMC packed moves。该轮启用 80 ms 延迟、2% 丢包，前踏 100 cm、一次扣费、最终误差约 0.029 cm。
- 以上 UDP 使用固定平地并关闭身体渲染，未覆盖真实敌人完整战斗、第三观察者、断线重连或全部坡面。隔离检查覆盖的取消／空中情况不能并称为 UDP 实测。
- 构建被共享任务覆盖时，保留实际成功日志、目标 DLL/EXE 和本轮源／对象对应记录。Editor 对象目录为 `UnrealEditor`，Game 为 `UnrealGame`，不能误读旧 `FPSGAME` 目录后声称已构建。构建与测试结果仍属于记录时的共享宿主，不证明公开切片独立可构建。

代码入口：`ProductionBluntSprint.cpp`、`ProductionBluntAuthority.cpp`、`FPSMeleeMovementNetwork.cpp`、`FPSDodgeNetwork.cpp`。历史回执与限定命令在 `SourceAssets/WarhammerSprintLunge20261025/CompletionReview`；恢复／发布范围在 `Docs/Publication/WarhammerRefinements20261025/README.md`。
