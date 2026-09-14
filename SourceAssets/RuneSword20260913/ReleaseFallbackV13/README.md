# ReleaseFallbackV13

2026-09-14：按用户要求，不足 2 秒松开右键也发动攻击。

- 未蓄满：进入普通 `Slash1`，普通伤害、速度、镜头和特效；蓄力抬剑进度映射到 V8 普通动作的对应蓄势位置，继续剩余动作。
- 满 2 秒：保持 `HeavyRelease` 和双倍武器伤害。
- 两种释放成功时均只扣一次近战体力；体力不足仍收回，收势可以接左键镜像下一斩。
- 更新物品操作提示与重击说明文档。

当前逻辑位于 `Source/FPSGAME/Weapons/RuneSwordComponent.cpp`，提示位于 `Source/FPSGAME/UI/ColdSteelItemTooltipData.cpp`。

必要 Editor 构建成功，退出码 0，耗时 113.65 秒，日志 `build.log`，模块保存于 `NativeBuildSnapshot/`。按用户规则未运行游戏测试、动画检查或渲染。
