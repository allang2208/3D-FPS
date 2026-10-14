# 第三人称上挑与冲刺竖劈

> 本版自编动作已被用户否定，不能作为认可动作模板。当前替换方案见 [第三人称全身素材与刃向修正](third-person-sword-donor-repair-20261006.md)。下文保留本版制作记录；旧 `publish_sword_actions_jason.py` 不再用于发布。旧作者输入中的骨架与装备待机标定继续供新适配脚本读取，不代表复用旧动作轨迹。

## 设计范围

用户要求按动作语义制作第三人称全身表现，不必逐帧还原第一人称。已有自制第一人称上挑继续作为语义与时序来源；本轮替换的是第三人称旧版整段倒放下砍的 Uppercut，另建 DashOverhead 动作。

- 上挑：双手将剑收到右下，屈膝沉髋蓄力，蹬地转髋并向前上方挑起，肘部承接高位余势，再回持剑姿势。
- 冲刺竖劈：短促举顶，沿正前方前送下砍，下压承接后回位；独立于普通 Overhead。
- 双手通过当前装备的待机握点标定保持同一剑柄关系，肩肘用固定骨长求解。头颈仅旋转，所有非骨盆平移和骨骼缩放采用 Jason 参考骨架。
- 保留原有下肢混合规则：低速站立时显示作者重心与前后脚支撑；移动时由现有走跑步态控制腿脚。根骨锁定，位移继续由玩法负责。

## 时序与接入

`FPSPlayerBodyActions.cpp` 将上挑实际 `ContactStart/ContactEnd` 和 `SwingRate` 传给第三人称表现。技能通常在源时钟 1.00–1.125 秒完成打击，动画总时钟 2.05 秒，仍由现有执行器控制。

`FPSBodySwordMotion.h` 新增 `DashOverhead` 变体到 `Melee.FullBody.DashOverhead` 的映射。冲刺原始时钟从 0.97 秒进入，1.22–1.40 秒命中，2.60 秒结束；新片段将其表现为 0.25 秒举顶、0.18 秒下砍及余下收势。

两个资产均为 30 Hz。Contact/Release 标记落在作者关键帧上，运行时现有分段采样器映射到玩法时钟。没有改动伤害、位移、攻击速度、第一人称动画、普通三连同首击的选择或旋风三阶段。

## 作者源与来源

- `SourceAssets/ThirdPersonSwordActions20261006/author_actions.py`：可编辑姿态、剑轨迹、骨长约束、肘面、腿脚支撑和阶段参数。
- 同目录 `authoring-input.json`：从已保存 Jason 骨架、KayKit 下砍及装备待机中导出的作者输入。
- 同目录 `authored-actions.json`：完整本机作者输出；属于密集骨采样，不作为公开源码素材分发。
- `Tools/PlayerBody/prepare_sword_actions_jason.py`：只读取已保存资产，不依赖活跃 PIE。
- `Tools/PlayerBody/save_sword_actions_jason.py`：后台创建两个独立包，保存成功后写 `assets-saved.json`。
- `Tools/PlayerBody/publish_sword_actions_jason.py`：仅发布两个已保存角色键，保留其他配置。

动作主体为本轮自制。冲刺躯干使用少量 [KayKit Character Animations 1.1](https://kaylousberg.itch.io/kaykit-character-animations) 的 CC0 下砍变化；[Quaternius UAL2 Standard](https://quaternius.itch.io/universal-animation-library-2) 的 Heavy Combo 用于上挑/下砍的重心与阶段参考，没有直接使用它分离的双手轨迹。官方免费包与许可留在 `SourceAssets/ThirdPersonSwordCandidates20261006`。第一人称输入只用于装备握点标定，不搬运其攻击手臂轨迹。

## 交付状态

已通过后台 Python commandlet 实际创建、压缩并保存两个 UE AnimSequence：

- `/Game/Characters/JasonPlayer20261003/SwordActions20261006/Animations/J_Sword_Uppercut`：62 个采样关键帧，原始长度 2.033333 秒，通过标记映射到技能时钟。
- `/Game/Characters/JasonPlayer20261003/SwordActions20261006/Animations/J_Sword_DashOverhead`：50 个采样关键帧，原始长度 1.633333 秒。

`Content/ColdSteelData/player_body.json` 已切换 Uppercut 并新增 DashOverhead。保存回执：`SourceAssets/ThirdPersonSwordActions20261006/assets-saved.json`；commandlet 日志：同目录 `save.log`。作者脚本与 C++ 接入已落盘，`FPSGAMEEditor Win64 Development` 后台构建成功；日志 `Saved/BuildEditor/build-20261006-132545.log`，本轮未启动编辑器。

没有运行游戏、PIE、渲染、截图或测试；实机观感由用户体验。
