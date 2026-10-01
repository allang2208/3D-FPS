# 陨星与冰墙的法杖限定（2026-09-30）

用户要求陨星、冰墙只能在装备法杖时施放。本次先覆盖这两项明确指定的技能。陨星此前已有 `requiresStaff` 判断，但配置为 false；冰墙最初迁移没有此限制。本次 `Content/ColdSteelData/skills.json` 两项均设置 `requiresStaff=true`，同步技能描述和快捷槽提示。

「装备法杖」指当前激活武器组主手为法杖，且没有切出采集工具；背包中的法杖或另一组未激活法杖不能满足条件。共用查询为 `UColdSteelStatusModel::HasEquippedStaff()`，沿用当前装备数据及只读 JSON 缓存。

- 无法杖时拒绝施法请求、撤销排队；不扣蓝，不启动冷却，快捷槽置灰并显示「需要法杖」。
- 实际起手扣费与发射接触点再次判断装备。陨星未释放前切走法杖取消手势、退还付款并撤销冷却；冰墙凝聚和预览阶段切走法杖清理种子／预览、退款并撤销预留冷却。
- 已释放的陨星及已发射或成形的冰墙继续按原生命周期结束。墙体不会因玩家换武器而消失，玩家可以换机枪使用矮墙脚架支撑。
- 冰墙的高／矮形态、放置、伤害、寒冷、修炼与存档口径沿用迁移方案；陨星数值、火场、素材和修炼不变。

触发和阶段入口为 `FPSFireMagicComponent`、`FPSIceWallComponent`；资源提交入口为 `ColdSteelFireMagicModel`、`ColdSteelIceWallModel`。冰墙补充配置解析及默认限定，陨星沿用既有配置开关。

本次 Game 与 Editor 目标均已完成后台构建并落盘，日志位于 `Saved/StaffRequired20260930/build-game.log` 与 `build-editor.log`。未启动编辑器、游戏、PIE 或测试，交由用户测试。
