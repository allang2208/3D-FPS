# 第三人称 Kwang 全身剑术接入

来源：用户已导入的 [Epic — Paragon: Kwang](https://www.fab.com/listings/f4c67e92-b976-4b5b-ab9f-4c25b010f6f3)。仅在本 Unreal Engine 工程中使用；原资源与派生动画不作为可再分发源素材公开发布。

保留当前 Jason 外观，重定向 Kwang 全身骨架动作。上挑采用 `PrimaryAttack_A_Slow` 的下沉后向上斩击；普通竖劈和冲刺竖劈采用 `PrimaryAttack_C_Slow` 的下斩；旋风采用 `PrimaryAttack_D_Slow` 的持剑转身横斩。`Ability_R` 包含剑脱手飞行，未用作持剑旋风。

最终动画位于 `/Game/Characters/JasonPlayer20261003/KwangSword20261006V2/Animations`，重定向中间资产位于 `KwangSword20261006`。原始 Kwang 资产只读。保留完整躯干、骨盆、腿部和主手路径，仅适配当前剑柄的双手握距、剑刃朝向、出入势与命中时序。刃面和长轴由 Kwang 原剑顶点推导；没有使用第一人称攻击曲线。

旋风分为起势、挥斩、收势三个连续片段，完整 D 段只播放一次。原动作的整体转向从骨盆坐标中消除，游戏原有旋风时钟负责角色转向，保留骨盆倾斜、高度、躯干相对转动和腿部蹬地/落地，避免双重旋转及重复起跳。攻击速度和命中停顿继续使用原武器执行器的时钟。

上挑、竖劈、旋风在移动时保留全身攻击权重。冲刺行进阶段使用原移动步态，到竖劈蓄力阶段才平滑切入全身动作。蹲姿、腾空、滑铲及攀爬仍保留原状态限制。新动画用 `NativeSwordGrip` 同步标记表明手臂已完成握持适配，运行时不再重复解算其双手 IK。

制作入口依次为 `Tools/PlayerBody/prepare_kwang_sword.py`、`retarget_kwang_sword.py`、`read_kwang_blade_geometry.py`、`SourceAssets/ThirdPersonSwordKwang20261006/adapt_kwang.py`、`Tools/PlayerBody/save_kwang_sword.py`。原始动作采样、几何、重定向中间资产和保存回执保存在本机。60 Hz 动画以完整 30 Hz 帧结束，适配 UE 默认压缩采样。六个最终动画保存、commandlet 正常退出及必要编译完成后，运行 `Tools/PlayerBody/publish_kwang_sword.py` 切换配置。

按用户规则后台制作、保存和必要编译；未启动编辑器、游戏或视觉验收，由用户测试动作效果。

交付状态：六个最终动画已保存，保存 commandlet 退出码为 0，运行配置已切换。Editor 构建成功，日志 `Saved/BuildEditor/build-20261006-234134.log`；保存日志 `SourceAssets/ThirdPersonSwordKwang20261006/save-v2.log`；切换回执 `SourceAssets/ThirdPersonSwordKwang20261006/assets-published.json`。
