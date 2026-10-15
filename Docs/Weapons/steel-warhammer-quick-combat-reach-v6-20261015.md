# 战锤快速近战：分阶段前捅 V6

后续用户指出左腕扭曲，当前动作引用已升级为 [V7 左腕与前臂修正](steel-warhammer-quick-combat-left-wrist-v7-20261015.md)。V6 保留为前伸轨迹与时序母版，V7 沿用本页的时长、接触和前伸数值。

用户认为 V5 仍僵硬，允许适当延长快速近战，并要求扩大前伸幅度。本版将战锤快速近战总时长从 0.5 秒延长到 0.72 秒，命中从 0.15 秒移到 0.28 秒。范围仅为双手战锤当前快速近战。

| 阶段 | 实际秒数 | 动作 |
| --- | --- | --- |
| 蓄势 | 0–0.22 | 收低对准，末段放缓，双手持续握柄 |
| 出手 | 0.22–0.28 | 加速向前直捅，锤头在 0.28 秒命中 |
| 卸力 | 0.28–0.34 | 接触后继续伸展，速度自然收敛，不插入静止帧 |
| 撤回 | 0.34–0.54 | 沿原方向撤回，肩肘随武器卸力 |
| 归位 | 0.54–0.72 | 放缓恢复原待机持握 |

最大前伸行程由 24 cm 增至 34 cm，命中时行程由 20.5 cm 增至 29 cm。保留 V3 的原生握距、包握姿态、原生骨长、完整剑类肩肘参考与前臂旋转分配；作者求解额外提供 4.5 cm 前向、1.5 cm 向下的肩部支撑，随后由原双骨链求解器补足。没有单独扳手腕、拉长骨段或松开手掌。

资产源仍为 0.5 秒参数化姿态，`WarhammerQuickCombatMotion.h` 的连续 Hermite 映射控制实际 0.72 秒播放。动画、镜头、精确接触姿态共用该映射；动作阶段、占用和技能预留时间读取实际时长，命中点仍在源 0.15 秒精确采样。保留 V4 的原生锤头坐标和枪械取消逻辑修复。伤害、技能查询范围、查询半径、体力数值与改造效果不变。

本版使用独立资产 `/Game/Weapons/SteelWarhammer20261014/QuickCombatReachV6/A_Warhammer_QuickCombat`，保留原 V3 资产。可编辑源、FBX、作者与导入脚本位于 `SourceAssets/SteelWarhammer20261014/QuickCombatReachV6/`。该目录 `authored.json`、`import_receipt.json`、`build_receipt.json` 和 `delivery.json` 分别记录制作、实际保存、构建与交付。

遵守用户规则，默认不运行游戏、诊断测试、预览或渲染；编译和资产保存不代表人体观感、穿模或打击手感已经验收，最终由用户体验。

## 本轮交付

后台导入进程 exit 0，动画编译完成并保存，`import_receipt.json` 为 `complete=true`、`HeadThrustReachV6_20261015`。排队后的 Game 与 Editor Win64 Development 正式构建均 exit 0 / `Result: Succeeded`，UBT 报告目标已是最新状态，相关源码已进入当前正式产物。V1/V2 兼容制作与导入入口已指向 V6，替换前入口保存在 V6 的 `Before/`。

交付回执为 `SourceAssets/SteelWarhammer20261014/QuickCombatReachV6/delivery.json`。没有主动打开编辑器、运行游戏、执行诊断测试或渲染，实际观感由用户验收。
