# 龙息“未就绪”：第一人称镜头与喷口校验

## 现场与原因

用户报告单人试玩、正常第一人称下，龙息起手后持续提示“龙息未就绪”。技能数据、起手、资源预留、持续伤害、联机状态和 Volume V8 资源均已有实现；此提示来自 `UFPSFireMagicComponent::ReleaseAtContact` 对所有 `StartDragonBreath` 失败分支的统一文案。

原喷口按 `Pawn.GetPawnViewLocation()`（胶囊眼点）为原点传输，但实际杖尖按第一人称 Camera 的世界变换生成。`player_body.json` 和 `FPSPlayerFirstPersonBody.cpp` 已把正常镜头前移 56 cm、蹲姿前移 62 cm，低头再加最多 12 cm，并保持身体前侧净空。原龙息校验仍限制前向偏移最多 140 cm，漏算了镜头位移。

本轮先增加具体拒绝原因，通过已有编辑器 Live Coding 接入。用户再次施法后确认看到“龙息喷口位置异常”；同次运行日志记录了五次单机拒绝：前向偏移 154.067、153.762、152.974、152.094、151.490 cm，侧向约 16–17 cm，竖向约 21–25 cm。全部超过旧的 140 cm 上限。现场证据：`Saved/DragonReadiness20261014/runtime-failure.log`，只读相机采样：`runtime-snapshot-mcp-02.json`。

## 修复

- 保留原胶囊眼点相对坐标与复制协议。在原有杖尖边界外增加 100 cm 镜头位移余量；俯仰会把镜头前移旋转到瞄准坐标的其他轴，因此同时考虑三个轴和总距离。
- 不把真实喷口夹回旧上限，不改伤害半径、等级、耗蓝、持续时间、冷却、专注或当前体积特效。
- 继续拒绝非有限数值、负前向位置以及超出有限空间范围的坐标；`DragonBreathFrame` 原有眼点到杖尖的墙体检查保持原样。服务端与本机调用同一入口。
- 原统一“龙息未就绪”改为具体的素材、装备、死亡、受控、喷口、预扣或提交失败提示；拒绝日志保留施法编号与坐标，提交失败另记档案错误。只在拒绝时记录，不增加逐帧日志。

## 针对性复现

`DragonBreathReadinessAudit` commandlet 创建唯一 `DragonAudit_<GUID>` 档案，只启动相关组件，不打开地图、游戏窗口或渲染。通过真实手势接触回调检查是否进入喷吐，并可用 `-CameraForward=56` / `62` / `74` 覆盖实际镜头位移。另检查过远、负向和 NaN 坐标仍被拒绝。

可选 `-SourceProfile=<slot>` 只读原存档，在独立测试槽中切换到该档案已装备的法杖。它不会修改原槽。早期探针首次没有推进异步加载回调，后续只在 commandlet 进程中禁用回调延迟；相关失败是探针环境问题，不能算作游戏资源丢失。最近试玩存档当时使用战锤，未切杖的副本会正确显示“需要法杖”，也不等于用户的原故障。

诊断补丁前的原生默认镜头（无前移）释放已通过：`before-r2.log`。修复后以下三轮 commandlet 均退出 0，`failures=0`：

| 镜头前移 | 档案 | 释放点前向偏移 | 结果 |
| --- | --- | --- | --- |
| 56 cm | 独立默认测试档 | 155.277 cm | 真实手势接触后进入喷吐 |
| 62 cm | 最近试玩档案的独立副本，切到已有法杖；施法速度 1.25 | 161.277 cm | 真实手势接触后进入喷吐 |
| 74 cm | 独立默认测试档 | 173.277 cm | 真实手势接触后进入喷吐 |

每轮还确认 400 cm 远端坐标、负前向坐标和 NaN 继续被“龙息喷口位置异常”拒绝。日志分别为 `after-camera56.log`、`after-camera62-profile.log`、`after-camera74.log`；原玩家存档没有被这些检查写入。这里验证的是相应位移下的原生释放路径，没有运行完整蹲姿/低头动画、渲染火焰或主客机网络传输。

## 最终构建与边界

相关源码最后修改于 2026-10-15 00:10:19 前。之后共享工程完整构建的最终回执已复制到 `Saved/DragonReadiness20261014`：

- `game-final-shared.log`：`FPSGAME Win64 Development`，完整 EXE 链接，`Result: Succeeded`，366.60 秒。
- `editor-final-shared.log`：`FPSGAMEEditor Win64 Development`，完整 DLL 链接，`Result: Succeeded`，20.27 秒；此前全量编译产物由这一轮增量链接完成。
- 三轮专项 commandlet 使用已保存的正式 Editor 模块，均在构建完成后运行。

最初的 Live Coding 仅加载诊断文案，用于捕捉用户现场；最终喷口修复现已进入磁盘上的 Game/Editor 正式产物。没有重新打开 GUI 编辑器或启动游戏；实际画面和联机表现仍由用户验收。

正式构建的共享前置错误为 `HeQueRiftPressure.cpp` 对 `TObjectPtr` 使用 `auto*` 推导，以及 `LargeLambMealAuditCommandlet.cpp` 对 `TSharedRef` 再调用 `ToSharedRef()`。分别只增加 `.Get()`、移除多余转换，保留原逻辑。失败回执为 `game-shared-before-compile-fixes.log`。先前为优先接入诊断而中断的 Game 构建不计作成功。
