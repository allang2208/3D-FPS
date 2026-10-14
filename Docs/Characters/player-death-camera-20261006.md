# 玩家死亡动作与同步镜头

## 设计

采用完整人形动作：受击失力、屈膝、向前倒下、落地停稳。第一人称相机使用同一动画导出的头部位置轨迹，旋转经过限制与落地回稳处理；不直接继承头骨的全部翻转。身体与镜头共享服务端死亡起点。

- 站立入口：1.4 秒完成倒地与收尾，约 1.0 秒触地。
- 下蹲/滑铲入口：从源动作已屈膝的位置进入，1.2 秒完成，约 0.73 秒触地。
- 第一人称：从上一帧实际视点接入，身体下沉、前倒，落地后保持低位；翻滚上限约 18 度，落地后看向低处前方。镜头使用球体扫掠及地面净空，避免直接穿入地面或墙。
- 第三人称：观察相机随倒地位置降低，保留后方观察距离；死亡动作播完保持最后一帧。
- 1.65–1.96 秒淡至黑屏，沿原有 2 秒重生流程更换 pawn，再释放本次淡出。
- 死亡取消正在执行的手部动作，收起视模及世界持械副本；装备与库存归属不变。第一人称显示倒地身体和衣物，头部/头发对本人隐藏；其他观察者仍看完整角色。

## 参考筛选

| 来源 | 本机读取结果 | 本轮用途 |
| --- | --- | --- |
| 原 `J_MM_Death_Front_01` | 约 1.1 秒，结束时骨盆仍约 80 cm 高、头部约 72 cm 高，身体未完整倒地 | 保留原资产；不再作为新死亡的运行入口 |
| [Kevin Iglesias Human Melee Animations FREE](https://kevdev.itch.io/human-melee-animatons-free) `HumanM@Death01.fbx` | 约 0.733 秒，包含屈膝、前倒和伏地收势；重定向末帧骨盆/头部约 11 cm | 本轮采用；调整节奏、地面支撑和 Jason 原生骨长 |
| [KayKit Character Animations 1.1](https://kaylousberg.itch.io/kaykit-character-animations) `Death_A / Death_B` | 本地 GLB 实际有 0.8 秒后倒与 2.633 秒前倒；简化卡通骨架 | 免费 CC0 参考，未发布为玩家动作 |

Kevin 的官方免费列表包含死亡动作。既有本地原包、许可和下载回执位于 `SourceAssets/ThirdPersonSwordFree20261005/`，按其 Standard Asset Store EULA 使用，原始 FBX、派生 uasset 和密集骨采样不作为公开源码素材分发。KayKit 候选读取结果位于 `SourceAssets/PlayerDeath20261006/kaykit-candidates.json`。

## 实现边界

- `UFPSCombatHealthComponent` 仍由服务端扣血、确认死亡并重生；先处理原地蟠桃续命，再发布死亡时间与姿态入口。客户端收到权威死亡后也停止动作与移动。
- 使用现有 `InterruptActionsForPriority(true)` 中断链，避免取消动作后用旧档案血量重新覆盖已死亡状态。
- `FPSPlayerDeathMotion.h` 定义共同时钟，死亡动作不使用客户端汇报的时间。现有身体状态与复制路径携带同一死亡起点。
- `FPSPlayerBodyDeath.cpp` 在既有 `CalcCamera` 路径生成最终视图，即使角色 Tick 已停止也继续表现；不修改射线瞄准或第一人称相机组件的玩法坐标。
- 相机轨迹随动画在离线作者阶段导出，只在初始化时读取；死亡窗口内每帧插值两个样本，没有第二次骨架动画求值或每帧磁盘读取。
- 当前采用固定前倒方向和动画末帧保持，没有加入物理布娃娃、击杀镜头、掉落装备实体或按受击方向选择多套死亡动作。

## 制作入口

1. `Tools/PlayerBody/prepare_player_death.py` 读取旧片段。
2. `Tools/PlayerBody/import_player_death_donor.py` 导入已有合法 Kevin 源并复用当前 Jason 重定向配置，写入新的 `Death20261006/Source`。
3. `SourceAssets/PlayerDeath20261006/author_death.py` 制作两个完整片段及同步镜头轨迹。
4. `Tools/PlayerBody/save_player_death.py` 实际创建、压缩和保存新动画。
5. `Tools/PlayerBody/publish_player_death.py` 只更新 `Dead`、`Dead.Crouched` 和匹配的镜头轨迹。

## 交付状态

已通过后台 commandlet 实际创建、压缩并保存：

- `/Game/Characters/JasonPlayer20261003/Death20261006/Animations/J_Death_Standing`：30 Hz、43 个关键帧、1.4 秒。
- `/Game/Characters/JasonPlayer20261003/Death20261006/Animations/J_Death_Crouched`：30 Hz、37 个关键帧、1.2 秒。

`Content/ColdSteelData/player_body.json` 已发布两个角色键及同步镜头轨迹。保存回执为 `SourceAssets/PlayerDeath20261006/assets-saved.json`，日志为同目录 `save.log`。作者源与 C++ 接入已落盘；`FPSGAMEEditor Win64 Development` 后台构建成功，日志 `Saved/BuildEditor/build-20261006-134208.log`。

本轮没有启动游戏、PIE、截图、渲染或运行测试，实机效果由用户体验。
