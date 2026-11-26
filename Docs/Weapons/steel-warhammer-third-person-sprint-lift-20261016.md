# 战锤第三人称冲刺举锤衔接

用户反馈冲刺攻击举锤时双臂相对固定、机械且扭曲，并明确本轮只处理第三人称。

## 原因

- `FPSPlayerBodyActions.cpp` 把 0.25 秒冲刺举锤标成普通 `WarhammerCharge`，导致 2 秒蓄力片段被压缩八倍，起点仍是待机而不是实际下拖持锤姿势。
- 原适配将对齐过的重定向骨骼旋转直接与 Jason 原生骨长组合，静态姿态基准不一致。原蓄力按冲刺时长采样时，左右前臂局部旋转最大单步分别约 138.5° 和 100.3°，双臂可达比最高约 0.975。
- 通用动作切换会混合 0.08 秒，而下砸接触发生在 0.075 秒；举锤到下砸被这次混合延后。原生双手动画在混合期间也没有重新约束两掌相对柄的关系。

## 本轮修改

- 新增 `WarhammerSprintLift` / `WarhammerSprintSlam` 两个表现变体和对应专用动画键。业务仍由原冲刺攻击执行器推进，举锤 0.25 秒、下砸接触 0.075 秒、接触停留 0.7 秒均不改。
- 从真实 `SprintCarry` 骨骼样本构建入口；以 Sevarog 的相对动作变化驱动 Jason 胸髋，取消不相容的静态参考偏移。手柄沿外侧弧线抬起，肩肘随身体发力；双手保持原生握距，手臂最大可达比收至 0.94，保留肘弯。
- 前臂角度连续展开，选择连续的肘弯平面，并沿原生 twist 辅助骨分配滚转。握柄处的掌向仍由同一个刚体关系决定。
- 在动作库未接管时缓存上一帧实际持锤姿态，用作下一次举锤入口；只有进入/退出混合期间补做双掌握柄约束，完整播放时沿用烘焙骨链。
- 专用举锤末帧与专用下砸首帧一致；这对片段之间跳过通用 0.08 秒混合。保留上一轮头部不追随镜头的修改。

## 定向排查结果与交付

本轮按用户“排查并调整”的要求，仅对这两段动作进行离线骨骼采样排查。最终举锤的左/右前臂最大 120 Hz 相邻采样转角为 11.75° / 9.49°；双掌握持关系最大位置残差小于 0.001 cm；两段交界平移一致，角度差仅为浮点舍入量。砸地停留段姿态保持连续。这些数值不代表运行时或视觉验收通过。

作者与记录：`SourceAssets/WarhammerThirdPersonSevarog20261016/SprintLiftV2/`，包括 `author_sprint.py`、`baseline.json`、`arm-diagnosis.json` 和 `adapted-actions.json`。

两段动画已由后台 commandlet 保存到 `/Game/Characters/JasonPlayer20261003/WarhammerSevarog20261016/SprintLiftV2/Animations/J_SevarogHammer_V2_{SprintLift,SprintSlam}`，回执 `assets-saved.json` 为 `complete: true`。`FPSGAMEEditor Win64 Development` 常规构建返回 `Succeeded / Target is up to date`，未强制重复构建；日志为 `Saved/BuildEditor/build-20261016-174817.log`，本批副本为 `SprintLiftV2/build-editor.log`。两条新引用已发布到 `Content/ColdSteelData/player_body.json`，发布记录为 `SprintLiftV2/assets-published.json`。

第一人称动画、攻击判定、体力、攻速和技能时间未修改。未启动游戏或进行 PIE、录像、渲染及联机验收。
