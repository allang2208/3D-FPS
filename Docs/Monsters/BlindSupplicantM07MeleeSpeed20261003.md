# M-07：横扫命中体与 1.5 倍移动速度

2026-10-03。用户反馈横扫没有伤害判定，并要求移动速度提高 50%、移动动画同步加快。

## 横扫

原伤害链路存在：攻击时钟到达 0.50–0.70 秒窗口后采样爪尖轨迹，命中玩家时调用 `ApplyDamage`，通过 `UEnemyMeleeDamage` 进入原伤害系统。原配置伤害为 36、基础近战距离 220 cm，统一倍率后的有效距离 330 cm。

从当前 V32 左右动画读取的接触姿态表明，在窗口内爪尖横向离正前方约 98–117 cm，手部关节约 53–64 cm。原半径 35 cm 的爪尖球体即使向前延长到攻击距离，仍会错过站在正前方的玩家胶囊。数据记录为 `SourceAssets/BlindSupplicantM07Meshy20261001/MeleeSpeed20261003/melee_source.json`；这是资产读取，不是游戏运行结果。

`SweepClaw` 改用覆盖手掌到爪尖骨段的胶囊体，保留 35 cm 厚度。胶囊方向随当前骨段，中心由原爪尖查询路径平移到骨段中点；原轨迹扫掠和向前延伸都使用同一形体。每个接触帧仍最多两次查询，仅在原短命中窗口执行，不新增 Tick 或额外骨骼刷新。

保持原攻击动作、0.60 秒接触中心、0.20 秒窗口、伤害、攻击距离、正前方限制、遮挡与冰墙判定。攻击只提交一次伤害，打断、死亡及弹反仍走原取消规则；不绕过玩家格挡、闪避或无敌状态。

## 移动

- 慢走速度：42 → 63 cm/s。
- 追击速度：86 → 129 cm/s。
- 动画源速度维持 42／86 cm/s，原 `实际速度 / 源速度` 播放逻辑因此在对应速度下达到 1.5 倍，不额外叠加 `RateScale`。
- 慢走／追击切换边界改用实际配置速度，切换滞后区间随两档速度差同步变化。原片段相位对齐和过渡保留。
- 只加快移动；近战、施法、受击和死亡播放速度保持原值。

## 接入

原生改动位于 `BlindSupplicantCombatMagic.cpp` 和 `BlindSupplicantMonster.cpp`。原 AI/F6 蓝图通过 `Tools/BlindSupplicantM07/save_melee_speed_20261003.py` 保存速度和移动组件默认值；备份位于本轮源目录 `Before`。

Game 构建完成：`Saved/BuildEditor/m07-FPSGAME-20261003-211846.log`。Editor 构建完成：`Saved/BuildEditor/m07-FPSGAMEEditor-20261003-212401.log`；正式 Game 可执行文件及 Editor 模块均已落盘。

原 AI/F6 蓝图已后台保存：`SourceAssets/BlindSupplicantM07Meshy20261001/MeleeSpeed20261003/ue_melee_speed_delivery.json`，`saved: true`，慢走 63、追击 129 cm/s；源动画速度仍为 42／86，近战配置未改变。保存日志为 `Saved/Logs/M07Import-20261003-212345.log`。

未运行游戏测试、PIE、截图或渲染，由用户体验。
