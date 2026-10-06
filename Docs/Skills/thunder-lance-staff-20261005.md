# 雷枪并入法杖限定（2026-10-05）

用户要求雷枪与冰墙等高级魔法一致，仅装备法杖时可施放。沿用 `requiresStaff` 数据开关与既有释放/退蓝约束，不新增独立检查通道。

## 数据与解析

- `Content/ColdSteelData/skills.json` 的 `thunderLance.requiresStaff` 置 `true`，描述前补「仅装备法杖时可施放。」；`stormDomain` 保持 `false`（两者共用 `FElectricMagicTuning` 但按各自定义条目解析，互不影响）。
- `FElectricMagicTuning`/`FElectricMagicCast` 新增 `bRequiresStaff`；`ColdSteelSkillRules.cpp` 电系块解析 `requiresStaff`；`ElectricMagicStats` 把标志拷进法术快照，蓄力期与服务端重算均可读到。

## 执行点（全部走既有契约）

- `ServiceQueue`：扣蓝/开手势前先判 `bRequiresStaff && !HasEquippedStaff()` → 反馈「需要法杖」、撤销排队，不扣蓝不进冷却。
- `BeginElectricMagicCast`（模型层）：同条件拒绝预留，双保险。
- `TickComponent`：已提交未释放（蓄力或手势中）切走法杖 → `CancelPending()` 退还付款并撤销预留冷却，反馈「需要法杖」。
- `ReleaseLance`：释放入口再查一次，覆盖切武器同帧按键的窗口。
- `NetRelease`（服务端权威重算）：影子档案 `HasEquippedStaff()` 再判一次，无法满足时拒绝（客户端 `NetCastRejected` 走原退款路径）。
- `ColdSteelQuickSlot`：电系分支追加 `ElectricMagicDefinition(Skill).ElectricMagic.bRequiresStaff` 判定，无法杖时置灰并显示「需要法杖」。

## 边界

已发射的雷枪束、命中、感电、修炼、联机复制与表现资产完全不变；数值与充能参数未动。源码已构建（`FPSGAME Win64 Development`），日志 `Saved/build-game-staff-gate.log`。未启动编辑器、PIE 或实机测试，交由用户验收。
