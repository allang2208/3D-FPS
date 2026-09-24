# 施法失败、打断与死亡时退蓝

2026-09-24。优先权打断已经会退还未释放法术的蓝；释放失败和死亡取消之前不会，冷却也停在已扣状态。

- 圣光、闪电、火系组件在释放失败和死亡时走 `RefundUnreleasedCast`：退蓝并回滚这次冷却。
- `ColdSteelFireballModel::RefundInterruptedSpellMana` 委托给 `RefundUnreleasedCast`，并清掉圣光、闪电、陨星、焰甲、火球、冰锥的冷却。
- 优先权打断先记下未释放技能名，再 `InterruptPending`，然后 `RefundUnreleasedCast`。
- 火球死亡只在本组件持有手势付款、且尚未提交发射时退蓝（`!GestureOwner && !bLaunchCommitted`），随后把 `GesturePaidMana` 清零。不要退掉别的法术已经记在火球组件上的付款。
