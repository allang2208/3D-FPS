# 缚群转向速度翻倍

> 历史阶段记录。2026-10-08 用户否定整体衣物并暂停；V18、V19 均未获认可。当前状态、最新参数和已归档证据的取回位置以[暂停与发布记录](bound-congregate-paused-publication-20261008.md)为准。

用户在移动速度翻倍后，要求转向速度同步翻倍。

## 修改

- 移动组件 `RotationRate.Yaw` 从 25 改为 50 度/秒，原地朝向目标也读取同一组件参数，替换原来的固定 25。
- 原地转身动画仍以源动作 14 度/秒为基准，按实际角速度计算播放速率。播放上限从 2.5 提高到 5，使 50 度/秒对应约 3.57 倍播放速度，不再被旧上限截断；保留原有接触相位和过渡。
- `Tools/BoundCongregate/set_turn_speed_20261008.py` 对正式 `BP_BoundCongregate` 设置绝对值 50，保留 RotationRate 的 Pitch/Roll，编译蓝图并保存。重复执行不会再次翻倍。
- 不更改接口或类布局，沿用现有移动组件生命周期和服务器原地朝向逻辑。攻击锁定、近战阶段朝向、触手 20 秒 CD 及此前移动参数不变。

## 接入状态

Editor 和 Game 的 Development 原生构建均已成功，正式蓝图已通过无界面 commandlet 编译保存。保存脚本读取到的新原生默认值已经为 50，并显式将蓝图移动组件设置为 50。

构建日志为 `Saved/bound-turn-build-editor-20261008-console.log`、`Saved/bound-turn-build-game-20261008-console.log`；保存结果为 `Saved/bound-turn-speed-20261008.json`，保存日志为 `Saved/bound-turn-save-20261008.log`。

本轮未测试，未运行转向探针、PIE 或画面验收，未打开 UE 界面。约 3.57 的动画播放速率为代码与参数对应的计算值，未报告为本轮运行实测值，由用户在游戏中体验。
