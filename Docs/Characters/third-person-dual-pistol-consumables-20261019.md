# 第三人称双持手枪：消耗品动作接管

2026-10-19。按用户要求检查双持状态下进食、喝药和收枪恢复的代码路径，并修正接管。没有启动编辑器、游戏或视觉验收。

## 现有动作覆盖

| 消耗品 | 第三人称动作 | 占用手 |
| --- | --- | --- |
| hp_potion、hp_potion_medium、hp_potion_high、hp_potion_special | Consume.Drink / WizardDrink20261010 原生手臂 | 左手 |
| mp_potion、mp_potion_medium、mp_potion_high、mp_potion_special | 同上，沿用既有共用瓶体握持 | 左手 |
| mineral_water、soda_can | Consume.Drink，按各自接触/恢复时序重定时 | 左手 |
| bread、roasted_chicken_leg、roasted_lamb_ribs、roasted_sausage | Consume.EatBread / FoodNative20261010，保留食物自己的接触配置 | 左手 |
| baguette_bread | Consume.EatBaguette / FoodNative20261010 | 左手 |
| roasted_large_lamb | Consume.EatLargeLamb / J_LargeLamb_TwoHands_20261017 | 双手 |

读取依据：Content/ColdSteelData/player_body.json、potion_use_motion.json、potion_visuals.json，以及 FPSPotionUseComponent、FPSGAMEConsumableUse、FPSBodyConsumePose、双持控制器和世界身体的采样/复制/动画分层路径。以上是配置与源码检查，不代表逐物品游戏验收。

## 修正

- 大份烤羊排开始前同时检查右枪动作、换弹、按住/待触发射击；使用期间双枪开火与换弹入口让位，覆盖收枪到抬回的完整时段。普通单手消耗品保留右枪独立行为。
- 身体状态明确传递消耗品占用手、实际收枪权重和藏枪窗口。第三人称采用同一 0.28 秒收起、物品自身使用时长、0.26 秒抬回时序，不再因 Consume 状态直接隐藏整个左枪过渡。
- 双持的肩部相对握姿始终作为进食层下方的底姿；收起时向身体两侧下方移动。手枪手臂拟合提前到原生消耗品层之前，保留已经认可的原生肘、腕、嘴部接触及双手大羊排姿态。
- 食物/药水手部样本不受枪械机械 rig 暂时不同步的屏蔽影响；动作通道切换时不在绝对腕坐标与手枪相对增量之间插值。
- 取消动作后为淡出中的进食手保留 0.1 秒藏枪；翻越、死亡和装备变化沿用优先级中断与同装备快照门槛。复制接管时同步新字段，清除非 Consume 状态的残留。
- 原有道具挂手、扣除/生效接触点、瓶盖/空瓶抛弃、口型/手指、下肢移动动画和资产均继续使用既有实现。

## 交付状态

源码已保存，FPSGAMEEditor Win64 Development 后台构建成功，退出码 0，耗时 35.91 秒；UnrealEditor-FPSGAME.dll 已链接落盘。日志：Saved/DualPistolConsume20261019/build-editor.log。

按上述分组核对现有 16 种物品及四条 Consume 动画资源路径，四个配置指向的 uasset 均存在。没有新建或重导入动画资产，没有进行游戏内、画面或联机运行测试。
