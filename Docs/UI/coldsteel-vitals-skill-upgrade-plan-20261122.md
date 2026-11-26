# 冷钢 UI 生命与魔法状态栏技能联动升级 · 2026-11-22

本轮接入左下角生命、魔法状态栏的技能体系（SKILL）联动升级。沿用当前冷钢 UI 正式规则及共享 `ColdSteelUIStyle`，保持 440px 紧凑 A 版外框及生存三项横排。按用户明确指令：**战斗态视觉收敛（折叠/收起生存栏）不实施**，生存指标保持原样常驻展示；重点落地槽体高度、刻度线、受击/消耗残影延迟条、法力蓄力预演与技能护盾叠层。

## 目标与交付阶段

- **名称与入口**：左下角资源状态栏（`UColdSteelHUDWidget::BuildTopVitals`、`RefreshTopVitals`）。
- **范围与用户已确定内容**：
  1. 槽体高度微调由 10px 提升至 13px，匹配冷钢微雕凹槽质感与 64×56 等级框比例。
  2. 100 点步长垂直暗细刻度线（Tick Marks），增强多阶法术与生命档位的心算可读性。
  3. 受击/消耗残影延迟条（`FColdSteelGhostTransition`）：掉血/耗魔瞬间真实条瞬降，残影延迟 0.22 秒后以三次缓动平滑追赶回缩；回血/回魔无延迟同步上升。
  4. 施法法力消耗预演（`PendingCostRatio`）：蓄力或准备阶段在法力条前端以金色脉冲条（`HUDGoldLight`）动态投影待扣减区间。
  5. 技能护盾 / 坚冰铠甲叠层（`ShieldRatio`）：存在护盾时以冰蓝色/银白叠层（`Layer + 5`）延伸显示，文本同步显示 `(+护盾)`。
  6. 排除项：按用户要求，不实施战斗态收起生存栏，饥饿/脱水/SAN 保持现行紧凑 A 版规则。
- **阶段**：游戏代码与自绘层正式接入。日常开发构建 `FPSGAMEEditor`。默认不启动编辑器、游戏、PIE 或实机截图，交由用户测试。

## 详细结构与主题规范

| 元素 | 复用主题 / 组件 | 规格与尺寸 | 渲染与表现 |
|---|---|---|---|
| 外壳 / 金角线 | `GlassTint` (#1A1A1AF8), `Border` | 440×184px, 圆角 10px | 1.25px `HUDGold` 四分之一圆弧与 6px 短切线 |
| 等级徽章 | `TopLevelSurface` | 64×56px 独立 Grid 列 | `Content` 墨黑底 + `HUDGold` 细线框，18 级大字 |
| 生命/魔法槽体 | `UColdSteelResourceMeter` | 高度 13px（原 10px） | 3*Unit 凹槽轮廓，内缩 2*Unit 墨黑内衬底 |
| 刻度分段 | 内部自绘 | 每 100 点 1px 细线 | `FLinearColor(1,1,1,0.18)` 半透暗白，不阻挡渐变 |
| 受击/耗魔残影 | `FColdSteelGhostTransition` | 延迟 0.22s, 过渡 0.38s | 生命受击为暗红/白半透，魔法为浅金淡蓝 |
| 施法预演 | `PendingCostRatio` | 动态脉冲 (6.0 rad/s) | `HUDGoldLight` 脉冲浮层 (Alpha 0.55~0.90) |
| 护盾叠层 | `ShieldRatio` | 覆盖当前生命之上 | 冰蓝 `FLinearColor(0.37,0.75,0.88)` 渐变 |
| 生存三项 | `SurvivalGrid` (饱腹/脱水/SAN) | 6px 细条，横排三列 | 保持现状，不收起、不隐藏、不改变逻辑 |

## 数据与动作合同

- **生命与护盾数据**：读取 `UFPSCombatHealthComponent::Health` 与 `MaxHealth`；护盾优先读取 `ActiveOvershieldAmount`，若角色挂载 `UFPSIceArmorComponent` 且处于激活期（`Remaining() > 0`），动态换算为冰甲吸收护盾。
- **魔法与预演数据**：读取 `UColdSteelStatusModel::Mana()` 与 `maxMp`；预演通过 `SetPendingSpellManaCost(Cost)` 驱动，无预演时保持 0。
- **刻度划分**：读取 `Maximum` 真实上限，动态生成步长比例 `100.f / Maximum`。

## 文件与构建

- 修改文件：
  - `Source/FPSGAME/UI/ColdSteelMeterPresentation.h`：增加 `FColdSteelGhostTransition` 结构，扩展 `PaintResourceMeter` 参数（带默认值，保证外部调用兼容）。
  - `Source/FPSGAME/UI/ColdSteelResourceMeter.h/.cpp`：增加 `SetPendingCostRatio`、`SetShieldRatio`、`SetMaxPoints`，自绘实现残影条、预演条、护盾叠层与刻度线。
  - `Source/FPSGAME/UI/ColdSteelHUDWidget.h`：增加 `PendingSpellManaCost` 与 `ActiveOvershieldAmount` 状态及蓝图方法。
  - `Source/FPSGAME/UI/ColdSteelTopVitals.cpp`：槽体高度设为 13px，`RefreshTopVitals` 接入上限点数、护盾与预演。
  - `Docs/Production/README.md`：登记功能条目与正式路径。
- 必要构建：后台常规构建 `FPSGAMEEditor Win64 Development`。未要求 Game 目标或打包，交由用户测试。
