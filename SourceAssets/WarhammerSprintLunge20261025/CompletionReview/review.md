# 双手锤冲刺攻击与第三人称完成度排查

范围：本段双手锤冲刺前移、第三人称腿部协调及对应联机通道。未重新验收之前所有锤头、符文、配重球、材质与特效。

## 发现并修改的源码问题

1. 远端玩家的服务器冲刺准备读取本地按键 / IsSprinting 状态，可能导致客机已准备、服务器仍拒绝释放。现改为读取 CMC 传输的奔跑意图，并保留已经挣得的空中准备状态。
2. 原移动请求未绑定具体锤子攻击。现使用 HammerDash / HammerAirMomentum 和攻击编号，锁定服务器出手方向，检查阶段与总距离预算，丢失步骤通过累计距离恢复，重复步骤不叠加。
3. 旧请求、换武器、死亡、取消和迟到拒绝可能留下惯性。现清理对应请求，预测回放不恢复已拒绝的惯性；单机与主机本地取消也清理惯性。
4. 可靠攻击 RPC 先于滑铲跳跃移动包到达时，过早停止移动会破坏跳跃。现由 CMC 先处理跳跃与当前移动标志，再承接实际服务器速度。
5. 胶囊前移未写入正常 Velocity，第三人称腿部可能停步滑行。现以真实位移驱动脚步；远端读取平滑后的身体位置。
6. 抬锤结束到下砸开始的腿部混合存在跳变，抬锤时钟也未正确跟随迅捷倍率。现使用跨阶段连续权重和与动作倍率一致的进度。

## 续修结果：2026-10-25 21:38

- 原构建阻塞已解决：当前 FPSGAMECharacter.h 已包含 UOffhandKukriComponent 的友元声明，副手上挑对 IsWeaponBusy 的访问可以编译。沿用工作区已有修复，没有重复改写该模块。
- 完整 FPSGAMEEditor 与 FPSGAME Win64 Development 构建均成功，DLL / EXE 已落盘。复用已成功的共享完整构建；分别核对了本轮源文件与目标文件时间。证据为 fixed-FPSGAMEEditor-receipt.json、fixed-FPSGAME-receipt.json、对应 shared.log 及 source-object-receipt.json。
- 隔离服务端检查通过 28 项、0 失败，进程退出码 0：authority.json、authority-receipt.json。覆盖准备状态、先移动后 RPC、重复 / 过期 / 取消请求、服务器方向与阶段距离、撞墙、空中速度、死亡 / 换武器、迟到拒绝、预测回放、体力归属及原生移动包序列化。它是直接调用权威处理器的夹具，不是 UDP 测试。
- 真实本机 UDP 主客机检查通过：Wire/20261025-213707/host.json 与 client.json，回执 wire-receipt.json。两端日志确认启用 80 ms PktLag 和 2% PktLoss；完整前移 100 cm，重复攻击只扣费一次（客机 100 -> 85，主机不扣），最终位置差 0.029 cm。覆盖实际可靠攻击 RPC、原生 CMC 移动包、体力回执和位置校正。
- Jason / Kaitlin 的原生动画图各完成 4 组采样：普通速度、另一种步态起相、2 倍动作速度、空中，共 8 组。capture-commandlet.json 退出码 0，native-graph.json、measurements.json 与 lower-body-review.png 已生成，均在 ../ThirdPersonReview/。离线蒙皮预览可见迈步到下砸支撑姿势的过渡；抬锤时长分别为 0.25 / 0.125 秒。

## 覆盖边界

UDP 检查为固定平地上的单个客机与监听主机，未渲染身体、未对真实敌人进行完整实战，也不覆盖断线重连、第三名观察者、所有地图坡面与所有装备组合。取消和空中情况由隔离权威检查覆盖，未将其描述为真实 UDP 用例。

姿态图来自实际 native graph 的离线骨骼与蒙皮采样，前移轨迹在采样器中重建；它不是游戏画面，也未包含最终武器、服装和地面 IK 的实机视觉验收。实机第三人称画面与操作手感仍由用户确认。

旧的 build_receipt.json、build-FPSGAMEEditor.log、attempt1 / attempt2 / attempt3 记录之前失败尝试；已退役日志与临时 CompileUnits 的具体归档位置见 Docs/Publication/WarhammerRefinements20261025/archive-manifest.json（尚需保留的证据仍在本地）；当前成功状态以 fixed-* 回执和上述运行结果为准。

未打开可见 UE 编辑器，未修改用户存档、关闭其他任务或发送跨任务协调消息。只停止了本任务多余的等待脚本，检查进程按本轮 PID / 命令行清理。
