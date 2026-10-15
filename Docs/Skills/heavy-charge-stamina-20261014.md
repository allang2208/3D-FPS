# 重击蓄力持续消耗体力

按用户 2026-10-14 要求，双手剑与战锤保持重击蓄力期间每秒消耗 2 点体力。达到满蓄力后继续按住仍持续扣除，不按蓄力进度封顶，也不受武器攻速或蓄力加速影响。

- 统一数值：`Content/ColdSteelData/skills.json` 的 `heavyStrike.heavyChargeStaminaPerSecond`；技能详情从同一配置显示消耗速率。
- `FPSStaminaModel.cpp` 的既有体力时钟负责结算，蓄力期间暂停自然恢复；右下角回满时间沿用同一活动状态显示暂停。
- 体力降至 0 时立即取消蓄力，不触发攻击，也不因继续按住而自动重新蓄力。双手剑复用蓄力收势，战锤沿已录制的蓄力路径平滑收回；双手、武器、镜头与第三人称表现同步过渡到待机。收势按 0.1～0.45 秒独立时钟执行，期间不再扣蓄力费，之后按既有恢复延迟回体。
- 松手、取消、换装或死亡结束蓄力扣费，已扣费用不退。释放攻击仍沿用原本一次近战体力成本，体力不足无法出手。
- 双手剑快捷栏自动蓄满释放也按实际蓄力期间扣费。
- 客户端蓄力表现与服务端影子档案分别在已有体力时钟结算。双手剑同步蓄力起止；战锤沿用既有蓄力 RPC，并补充服务端中断清理。无需逐帧发送扣费请求。

交付边界：源码及数据落盘。本批改动的源文件已在现有 FPSGAMEEditor 构建中完成对象编译，但完整构建失败，未生成本次完整 Editor 产物。日志保存在 `Saved/BuildEditor/heavy-charge-stamina-editor-20261014.log`。

构建阻断来自并行制作中的 `ColdSteelQuickSlot.cpp` 局部 `Item` 遮蔽、`FPSGAMECharacter.cpp` 未声明的 `ProductionTools`，以及 `ProductionBluntWhirlwind.cpp`／`ProductionToolMotion.cpp` 缺失的 WhirlwindFocus 方法。本次保留这些文件；结束时已有 FPSGAME 编辑器进程在运行，未关闭或重启。未运行游戏、联机测试或画面验收。

## 体力耗尽收势补充

后续用户明确要求归零取消。已接入共用体力结算的当帧取消、双手剑现有收势、战锤反向收势及镜头／第三人称同步；蓄力入口与松手入口同时拒绝零体力，取消后清除自动释放和连击排队。

该补充期间现有 Editor 构建最终失败于并行文件 `ProductionBluntWhirlwindFocus.cpp:25` 的 `uint8` 到 `bool` 列表初始化收缩转换，日志：`Saved/BuildEditor/heavy-charge-exhaustion-editor-20261014.log`。完整构建产物尚未生成，未对自然收势或联机执行运行测试。当前编辑器保持原状。
