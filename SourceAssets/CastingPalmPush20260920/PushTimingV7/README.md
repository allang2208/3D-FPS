# 推掌 V7：双倍推出速度，总时长不变

用户要求发射时手掌推出速度加倍、停顿加长、总时长不变。只重定时 V6 的推掌与停顿，不改变其手型、前臂求解、预备和收手动作。

| 阶段（默认施法速度） | V6 | V7 |
| --- | --- | --- |
| 预备 | 0.26 s | 0.26 s |
| 推掌 | 0.34 s | 0.17 s |
| 到位停顿 | 0.30 s | 0.47 s |
| recover | 0.50 s | 0.50 s |
| 独立释放总时长 | 1.40 s | 1.40 s |
| 从推掌开始至发射触发 | 0.20 s | 0.10 s |

`FireballCastMotion::ReleasePushSpeed=2` 统一压缩推掌姿态采样和接触触发。`ReleaseDuration`、`LaunchContactTime` 保留原作者时钟，运行时分别除以该倍率；Releasing 的阶段结束时刻保持原值。姿态提前到达终点后继续保持，省下的时间全部进入停顿。若施法速度为 S，推掌为 `0.17/S` 秒，停顿为 `0.30+0.17/S` 秒，独立动作总长仍为 `1.10/S+0.30` 秒。

`../../FireballCast20260914/author_cast.py` 默认输出本目录，按相同倍率同步接触与停顿，烘焙 300 Hz 可编辑 Blend 和九段 FBX；总长仍为 1.40 秒，PushHold 为 0.47 秒。游戏继续使用共用程序化左臂层，FBX 是可编辑源交付。V6 及其检查记录保留，本轮未运行测试、PIE、姿态检查或渲染。

当前编辑器先通过 Live Coding 编译应用改动，未中断当时正在运行的游戏。`FPSGAME Win64 Development` 常规构建完成后，编辑器已无游戏运行和未保存包，正常退出并完成 `FPSGAMEEditor Win64 Development` 常规构建，再重新打开项目。两目标均成功，基础 Editor DLL 与独立游戏程序已更新。日志为 `live-coding-response.txt`、`build-game.log`、`build-editor.log`；未启动游戏测试或生成预览。
