# Wizard 喝药动作接入第三人称角色

使用用户已下载并导入的 [Dungeon Mason — Wizard for Battle: PBR](https://www.fab.com/listings/a42813d8-92bd-4ee4-a3de-fd12f568ded2)。源为 `/Game/BattleWizardPBR/Animations/PotionDrinkAnim`，左手动作，约 2.667 秒。

## 制作与接入

- 在独立 `WizardDrink20261010/Rig` 目录创建 Wizard → Jason 的 IK Rig / Retargeter，并保存完整重定向供体。原下载包未改动。
- 动作保留源肩肘运动和头部饮用节奏，按 Jason 原生骨长制作；躯干、头部变化适度收敛。源角色手部简化，最终手指继续使用现有 V7 抓握映射。
- 将腕部轴向旋转分配到前臂，手腕只保留小幅转动及柔和侧弯；前臂加权辅助骨按位置分配旋转。没有拉长骨段、改皮肤或使用第一人称手腕轨迹。
- 作者拟合和运行时瓶口补偿均把“前臂—手腕—所握容器”视为保持局部关系的整体，以瓶口对准嘴部求肩肘位置。新的 `NativeConsumeArm` 标记启用该路径，避免位置 IK 之后再次强制覆盖手腕世界方向。
- `Contact` / `Release` 使用新序列的 0.4 / 0.75 进度，运行时继续映射到当前物品自己的饮用开始、结束时刻。库存扣除、恢复数值、瓶塞、液面、抛瓶、第一人称及右手装备规则沿用原实现。

正式资产：`/Game/Characters/JasonPlayer20261003/WizardDrink20261010/Animations/J_Wizard_Drink_NativeArm`。

配置仅替换 `Content/ColdSteelData/player_body.json` 的 `Consume.Drink`。该入口覆盖当前喝药、喝水和汽水；`Consume.EatBread` / `Consume.EatBaguette` 保留原序列，本包没有进食动画，不将本次饮用适配当作进食修复。

## 制作源与恢复

工具：`Tools/PlayerBody/read_wizard_drink20261010.py`、`prepare_wizard_drink20261010.py`、`author_wizard_drink20261010.py`、`save_wizard_drink20261010.py`。

必要构建中发现 `SpellbookFocusPose.cpp` 仍按数组索引读取已经变成 `FQuat` 的 `Key.Rotation`。本次仅将该读取改为 `Key.Rotation.GetNormalized()`，不改魔法书关键帧或动作行为。

输入、作者关键帧、保存回执与构建日志在 `SourceAssets/ThirdPersonWizardDrink20261010/`。`assets-saved.json` 记录旧饮用动画引用和新资产源散列；原 UAL2 序列保留。下载包、源关键帧及派生动画仅用于当前已授权项目，不据此视为可公开再分发。

## 交付边界

源动作读取、整臂制作、资产保存与必要构建已完成。游戏版构建成功；编辑器基础构建返回 `Succeeded`，目标已是最新。构建记录见 `SourceAssets/ThirdPersonWizardDrink20261010/delivery.json`。

没有主动启动游戏、截图、渲染或额外运行测试；最终自然度、服装变形、容器与嘴部接触由用户在游戏中确认。

## 后续状态（2026-10-10）

用户随后明确反馈喝药没有问题。进食后来单独采用当前饮用手臂作为制作参考，并完成最终上臂修复；当前入口与用户“基本OK”的反馈见[进食记录](third-person-food-native-20261010.md)。上文“进食保留原序列”描述的是本次饮用初次接入阶段，不是当前进食配置。饮用资产保持认可版本；完整恢复和发布边界见[发布说明](../Publication/ThirdPersonActions20261010/README.md)。
