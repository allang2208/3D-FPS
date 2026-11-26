# 双手锤第三人称居中持握 V12

2026-10-17。用户指出待机上半身歪向一侧，并要求第三人称独立于第一人称调整。本轮同时延续此前尚未发布的持锤走跑优化。

## 原因

本轮开始时配置仍引用 CarrySprintV10；V11 的 17 个移动资源已保存，但未发布。Kwang 原待机是有明显高低肩的持剑姿态：Jason 重定向帧 0 的左右肩高度差约 13 cm。V10 仅用肩线的水平投影修正朝向，未消除肩线倾斜和躯干偏斜。结果 Carry 帧 0 的骨盆到上胸方向横向偏约 12.28°，肩线倾斜约 27.97°。运行时的上身覆盖保留了该不对称。这里是源姿态选择和适配的不足，不是要求第三人称跟随第一人称的结果。

## 调整

- 采用现有 Jason/Manny 第三人称自然站立呼吸和八方向徒手走跑素材。Kwang 旧待机不再作为躯干、肩线基准；只复用已有持锤的手臂初始姿态，随后重新求解双手握持。
- 用居中的脊柱与平衡肩线替换源素材的固定朝向偏差，站立轻微前倾 3°、跑动与冲刺预备 6°。保留素材中随时间变化的胸部运动、肩肘配合、骨盆、根、腿部及脚步标记。
- 使用实际装备的静态掌部握距约束同一根锤柄，保留屈肘空间、肩胸前方空间及柄尾和锤头的前方距离。第一人称动画轨迹不进入制作过程。
- Idle 与八方向 Walk/Jog 构成完整的 17 动作家族；另保存 SprintCarry，共 18 个独立新资产。普通 Carry 回退引用同一个新 Idle，避免回退到歪肩姿态。
- 继续使用 V11 已实现的全身步态混合与步频逻辑，不再用独立待机上身覆盖移动中的胸部，也不再经过固定手腕锚点的通用 IK。攻击素材、伤害、攻速、旋风方向和头颈稳定逻辑没有改动。

## 制作与接入

作者目录：`SourceAssets/WarhammerThirdPersonSevarog20261016/CenteredCarryV12/`。

制作入口：`prepare_centered_carry_v12.py` → `CenteredCarryV12/author_centered_carry.py` → `save_centered_carry_v12.py` → `CenteredCarryV12/publish.py`。

独立资源目录：`/Game/Characters/JasonPlayer20261003/WarhammerSevarog20261016/CenteredCarryV12/Animations/`。

配置角色共 19 项：`Warhammer.Idle`、`Warhammer.Walk.{八方向}`、`Warhammer.Jog.{八方向}`、`Warhammer.FullBody.Carry`、`Warhammer.FullBody.SprintCarry`。

本轮没有修改 C++。此前阻塞 V11 的天气构建问题已在后续工程构建中解除：`Saved/BuildEditor/weather-equipment-20261017-editor.log` 在 14:22 完成正式 Editor 构建并返回 `Result: Succeeded`，当前 DLL 新于身体动画源码。本轮发布使用此已有构建作为接入前置，并保存其日志副本，不冒充本轮重新编译。所有新包后台独立保存，不覆盖编辑器加载的旧包。

18 个新动画包已在后台实际保存，保存 commandlet 于 14:52 完成，退出码 0。随后发布脚本完成 19 项配置引用替换，`assets-published.json` 已落盘。制作数据中 Idle 的平均横向倾角约 -0.008°、平均肩高差约 0 cm；保留了随呼吸变化的小幅动作。

新角色组件初始化时从配置加载新版，因此已在运行中的游戏需要退出本次游玩再重新进入。本轮未改 C++、未关闭或重启用户编辑器。制作约束数据不代表视觉或运行验收；未启动游戏、截图、姿态渲染或运行测试。

## 后续握持修订

用户随后提供截图，否定 V12 的待机手臂观感。18:11 已发布 [V13 手臂握持修订](steel-warhammer-third-person-relaxed-grip-v13-20261017.md)：保留 V12 身体及脚步轨道，重排双肘、降低斜持握姿并减小腕部偏折，同步处理上臂和前臂扭转辅助骨。当前 19 项引用指向 RelaxedGripV13；V12 不作为已认可手臂姿态。
