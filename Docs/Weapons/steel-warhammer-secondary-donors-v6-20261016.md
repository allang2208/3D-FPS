# 双手锤第三人称旋风、格挡与快速近战：现成全身素材 V6

> 2026-10-16 用户实际反馈：整套表现不合格，且第三人称能看到额外一套第一人称手臂或武器。本版仍未获认可；下述构建与保存记录不代表动作质量通过。重复手臂修复见 [装备副本手臂泄漏修复](steel-warhammer-world-arm-sections-fix-20261016.md)。

后续关节适配返工见 [V7](steel-warhammer-anatomical-grip-v7-20261016.md)。本页保留 V6 的历史制作说明，不将原有握柄解算当作已认可方法继续复用。

本轮延续 V5：使用现成第三人称素材，不读取第一人称攻击轨迹或重建手臂/锤头运动路径，头颈保持稳定。

## 动作覆盖

| 状态 | 素材与接入 |
| --- | --- |
| 旋风准备 | 现有 Jason/Kwang `Whirlwind_Start` 完整段 |
| 旋风旋转 | 现有 Jason/Kwang `Whirlwind_Loop` 原旋转段，随技能旋转阶段播放一次 |
| 旋风收势 | 现有 Jason/Kwang `Whirlwind_End` 完整段 |
| 抬挡 | KayKit `Melee_Block` 的原始抬挡段 0–0.4 秒 |
| 持挡 | KayKit `Melee_Blocking` 完整原生循环，经已有 Jason 重定向器导入本批独立包 |
| 提前松挡 | 反向播放同一抬挡段，保留当前抬挡进度 |
| 完全抬挡后松挡 | 反向播放同一抬挡段，并由现有退出状态交还持锤姿态 |
| 格挡受击 | KayKit `Melee_Block_Hit` 完整承力和恢复段 |
| 破防 | 复用同一全身受击素材，按既有破防持续时间播放；保留已有受控反应层 |
| 快速近战 | KayKit `Melee_Block_Attack` 完整前送推击与回收段 |

格挡/推击素材原本以前侧左掌承力。本批保留素材中的躯干、腿部和主动掌轨迹，以一次静态横柄标定将锤接到该掌，另一手仅做实际握柄接触适配。旋风保留现有 Kwang 右掌轨迹和完整身体动作，仅适配锤的掌柄关系。没有参考第一人称举挡、头锤或旋风手臂动作。

所有新素材固定 `neck_01 / neck_02 / head` 的局部中立姿态，运行时继续使用 V5 已有的头颈稳定覆盖，头部仅跟随身体。

## 运行边界

- 新增九个 `Warhammer.FullBody.*` 角色键，复用七个实际动作包；退挡复用抬挡，破防复用全身受击。
- 工具状态传递进入、保持、退出、受击和破防语义。提前松挡反向进度支持现有网络有符号速度字段。
- 新路由使装备和手指继续使用静态握柄绑定，停止把第一人称动态手腕叠加在这些全身动画上。
- 旋风使用已落地的 Kwang 原始分段衔接；角色本身承担技能转向，不套用双手剑的反向旋转补偿。
- 持挡使用素材本身的循环。移动格挡保留现有行走腿部，原地使用素材的承重站姿。
- 快速近战保留一个战斗接触锚点，之后使用素材自身回收。
- 第一人称动画、伤害、耗体、冷却、格挡/弹反/破防判定与技能位移未修改。V5 普通攻击、重击、上挑、冲刺攻击引用不变。

## 制作与落盘

- 输入读取：`SourceAssets/WarhammerThirdPersonSevarog20261016/prepare_secondary_donors.py`
- 作者目录：`SourceAssets/WarhammerThirdPersonSevarog20261016/SecondaryDonorsV6/`
- 主脚本：`adapt_secondary.py`，素材输入 `sources.json`，输出 `adapted-actions.json`
- 保存入口：父目录 `save_secondary_donors.py`，使用现有无界面 commandlet 与批次互斥
- 新包目录：`/Game/Characters/JasonPlayer20261003/WarhammerSevarog20261016/SecondaryDonorsV6/Animations`
- 保存/切换回执：`assets-saved.json` / `assets-published.json`
- `publish.py` 仅在正式 Editor 构建完成后写入这九个新键。

## 交付状态

七个素材适配包已由后台 commandlet 保存。正式 Editor 构建成功，运行接入源码已编入 `UnrealEditor-FPSGAME.dll`，随后完成九处配置切换。构建日志为 `Saved/BuildEditor/build-20261016-212706.log`，本批输出为作者目录 `build-editor.log`。

未启动编辑器、游戏、PIE、测试、截图或渲染，实际效果由用户体验。
