# 弓腰射构图、准星与散布（2026-09-26）

用户反馈待机偏左遮挡视野，并要求弓具备类似枪械的腰射随机散布与 ADS 精确瞄准。本批保留木质长弓、V10 动画、0.2 秒举弓和上一批箭台侧置参数。

## 构图

参考当前角色默认 M4 视模的右侧、低位构图（M4 组件偏移 `0,7,-7` cm）。弓与枪的原生骨架原点不同，因此不直接照搬枪的组件坐标。

弓新增 `bow_hip_offset_cm = 0,12,-6`：在原动画上将手臂和武器共同右移 12 cm、下移 6 cm。待机握把由约 `46,-20,-20` 变为 `46,-8,-26`，同时作用于腰射举弓／拉弓／回收。满 ADS 使用已有瞄准对位，腰射偏移随 ADS 权重退出；下蹲姿态继续围绕握把叠加。

## 准星和实际发射

- 复用 `ColdSteelCrosshair.cpp` 的四线准星与 `GetCrosshairHalfExtent()` 的投影，兼容 FOV 和 UI 尺寸。弓不受仅允许枪械显示准星的旧门槛限制。
- `UBowWeaponComponent::ShotSpread()` 同时供 HUD 和发射方向读取。和枪械一样，在相机右／上两个方向分别均匀随机取样，再沿这条散射射线求目标；不把腰射重新引向原中心目标。
- 静止腰射基础斜率为 `0.035`，单轴约 2°；移动最多增加 `0.04`，腾空增加 `0.05`，蹲姿乘 `0.7`。成功腰射后额外扩张 `0.012`，每秒恢复 `0.06`。移动、腾空和蹲姿变化沿用连续权重，避免准星突变。
- 散布乘 `(1 - AimAlpha)`，只有 ADS 完全到位才归零。四线准星同步收拢淡出，留下一个小型中央瞄准点。收弓、装备未就绪、冲刺、翻越或菜单期间按现有状态隐藏。
- 箭从真实箭尖出发，按当前箭速与重力求到散射目标的低抛物线方向；满 ADS 的目标位于中央瞄准射线。因此保留箭的飞行时间、重力和途中障碍，同时避免单纯去掉随机数后仍固定打低。无可解轨迹时沿现有直指方向释放；移动目标仍需预判。

参数保存在 `Content/ColdSteelData/bows.json` 的 `bow_hip_*`、`bow_move_spread`、`bow_air_spread`、`bow_shot_spread`、`bow_spread_recovery` 与 `bow_crouch_spread_scale`。表现版本升到 18，由现有档案迁移更新已有弓。计算在弓原有动作 Tick 中推进，不新增 Tick、文件读取或每帧属性目录求值。

## 交付记录

源码与配置已落盘。用户关闭编辑器后已完成后台 `FPSGAMEEditor Win64 Development` 构建，结果 `Succeeded`。首次构建被地下城 `FSocket` 同名类型歧义阻断；重试前该行已由并行修改补全命名空间，本批未改动该文件。重试报告目标已为最新，日志：`Saved/BowAudioStillNorth20260926/build-bow-hip-fire-20260926-retry.log`。未启动编辑器、游戏、射击测试、截图或渲染，观感与命中效果由用户测试。

修改前文件：`Saved/BowHipFire20260926/Before/`。涉及 `BowWeaponComponent.h/.cpp`、`FPSGAMECharacter.cpp`、`ColdSteelCrosshair.cpp` 和 `bows.json`。
