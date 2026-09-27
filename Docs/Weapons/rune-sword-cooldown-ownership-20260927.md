# 符文长剑命中冷却特性的武器归属

用户于 2026-09-27 指定：命中减少全部技能冷却 0.5 秒属于符文长剑，高地双手剑应剔除该效果。

原来 `URuneSwordComponent::StartSwing` 与 `BeginWhirlwind` 在所有共用双手剑动作的武器上都设置基础 0.5 秒。现于出手时按物品 Definition 固定结果：仅 `ue_rune_sword` 获取基础 0.5 秒及其金色符文附加值，其他剑为 0。普通挥击、重击、突刺、配重快速近战和旋风的确认命中入口都只在数值大于 0 时提交冷却缩减；保留同一次攻击只结算一次的既有规则。冲刺等原有置零路径保持不变。

只修改 `Source/FPSGAME/Weapons/RuneSwordComponent.cpp` 与 `RuneSwordWhirlwind.cpp` 的现有函数体；不新增反射字段，不改变技能冷却数值、魔法冷却倍率改造、攻击时序、伤害或存档。当前脏文件内其他修改保留。

已通过现有 UE 会话与互斥桥完成 Live Coding：UBT 返回 `Result: Succeeded`，引擎于 2026-09-27 05:44:39 UTC 记录 `Live coding succeeded`，补丁已应用当前进程。本轮交付为源码与热编译补丁，没有执行关闭编辑器后的常规基础 DLL 构建。结果摘录位于 `SourceAssets/HighlandClaymoreMeshy20260922/WaveBladeConcept20260927/cooldown-compile-result.txt`。

没有启动或重启 UE，没有启动游戏、测试或验收。新设计的破阵波刃仅为概念预览，与本修正独立交付。
