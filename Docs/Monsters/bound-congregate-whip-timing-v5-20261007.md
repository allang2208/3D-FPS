# 缚群 V5：三倍出手速度与分段节奏

> 历史阶段记录。2026-10-08 用户否定整体衣物并暂停；V18、V19 均未获认可。当前状态、最新参数和已归档证据的取回位置以[暂停与发布记录](bound-congregate-paused-publication-20261008.md)为准。

用户要求将挥鞭出手加快到三倍，不做线性播放，并明确截断、分段。

- 保留 V4 原始触手网格、肩部权重、物理波形和现有蓄力长度。出手总长由 0.62 秒改为 0.206666667 秒。
- 出手使用分段 Hermite 曲线：前 14% 时间播放源动作 0—6%，中间 66% 时间爆发推进到 94%，最后 20% 时间短收束至末帧。段内速度变化，接点相位和速度连续；没有重新直线插值触手的空间轨迹。
- 动画代理和打断状态共同使用 `BoundCongregateTentacleTiming.h` 的相位。出手限速同步总倍率和曲线速度，避免时间变短后可见触手被旧限速拖慢。
- 命中时立即截断甩击、从当前可见姿态进入缠绕。落空时只等待终末姿态参与下一帧扫掠，取消旧固定 0.1 秒拖尾；随后进入独立 0.65 秒收势。
- 收势开头保留约 0.039 秒短停，之后采用缓入缓出相位恢复，不将蓄力、出手、缠绕和收势一起加速。释放缠绕时采用与可见缠绕一致的相位。
- 原 `BP_BoundCongregate` 保存新的出手时长，F6 入口不变。V4 模型重导入脚本同步此默认值。

制作与接入文件：`BoundCongregateTentacleTiming.h`、`BoundCongregateTentacleControl.h`、`BoundCongregateTentacle.cpp`、`BoundCongregate.h`、`save_tentacle_timing_v5.py`、`finish_tentacle_timing_v5.ps1`。

Editor / Game 后台构建均成功，`BP_BoundCongregate` 的新时长已由 commandlet 实际保存；构建日志及 `delivery.json` 位于 `SourceAssets/BoundCongregateMeshy20261006/TentacleTimingV5/`。本轮未运行测试、动作检查、预览渲染或游戏；V4 的旧动图和 300 帧检查不代表 V5 已经验证，由用户测试。
