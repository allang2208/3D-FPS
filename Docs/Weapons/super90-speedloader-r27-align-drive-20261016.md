# Super90 快速装填 R27：保留 R25 对准，重做加速推入（2026-10-16）

用户体验 R26 后认为“还是原来的节奏相对好，有一个对准然后加速推入的过程”，要求按这个思路重新设计。R26 为了去掉 R25 慢段中途的近停，把对准段拉成均匀的 0.26–0.30 倍；结果对准时刻消失，和推进的对比也弱了。那个近停其实就是用户感到的“对准”。

## 节奏设计

`r27_timing.py` 生成 `Source/FPSGAME/Weapons/Super90LoaderPushTiming.h`。分界与总时长不变：30% 行程在 pace 104（源 92.50245），压实在 pace 116，额外 6 个属性帧。

- **对准段 pace 86–104：原样保留 R25**（同一 Hermite 节点）。对接后逐步减速，在 pace 96 附近降到约 0.12 倍形成对准停顿，再起步。
- **推入段 pace 104–116：重做**。R25 峰值在 pace 110，113 节点处有一次回落再上升（1.73→1.46→1.62），最后三帧收力，到底偏软。R27 从 0.62 倍连续单调加速，峰值约 2.28 倍（pace 114.4），只在最后一帧制动接压实。
- 安装的推杆在源帧 104–110 本身越推越慢，所以按“推杆每 pace 帧的行程”设计：R25 为 2.8→7.7（pace 109 峰值）→ 降到 4.9；R27 为 2.8→3.4→4.2→5.1→6.1→6.8→7.3→8.0→8.4（pace 113）→ 7.7→7.3，接着压实。见 `timing_comparison.json`。
- 原声：对接 pace 87.11（与 R25 相同），推动瞬态 pace 110.65（R25 为 109.37，仍在加速段内），压实 116。原声和枪身响应都在源时钟上，运行时反算，不需要改。

## 动作层

R26b 的左手层（握钮上的蓄腕／回正、剥离、手指拖尾、源帧 115–123 去停顿）设计不变，按 R27 时钟重新采样（`author_r27.py` 调用 R26 的 `author_r26.py`，底稿仍为 R26 前的安装版）。源帧 124 之后手位与安装版一致，脱离原声对齐保持。作者侧检查：手腕只在源帧 88–122 有改动，骨长误差 <1e-6 mm。

## 接入

- 保存：`save_assets.py` 只接受当前安装的 R26b 包（`r26b_saved_sha.json`）与 R26b 握把条目；覆盖前的 R26b 包放在本目录 `Before/Content`，R26 头文件放在 `Before/Source`。
- 需要常规 Editor／Game 构建，因为时钟头文件变了。
- **已保存**：UE 关闭后经后台 commandlet 保存 18 项（14 段动画 + 四份握把 Profile），回执 `save_receipt.json` 为 `Super90LoaderR27-20261016`、`completed=true`，18 个包均已不同于 R26b。`read_saved.py` 读回压缩后数据：normal_1／normal_7／empty_7 的 hand_l 与 R27 数据相差 0.000°，源帧 60、130 与 R25 一致；vertical Profile 的 14 个条目一致。
- **已构建**：头文件 17:22:40 写入。另一会话 17:22:53 开始的 Editor 构建已重编 `FPSGAMECharacterSuper90.cpp`、`ColdSteelSuper90Authority.cpp`、`FPSGAMECharacterReloadCamera.cpp`，`UnrealEditor-FPSGAME.dll` 17:23:42 写出。Game 目标由本轮 `build_native.ps1 -Targets FPSGAME` 构建成功（`build-FPSGAME-20261016-172703.log`），同样重编了这三个文件。

## 恢复

- 回到 R26b：放回本目录 `Before/` 的包和头文件。
- 回到 R25：使用 `Super90LoaderR26_20261016/Before/` 的包，以及 R25 头文件（`Super90LoaderR26_20261016/Before/Source`）。

两种都要重新构建。没有启动游戏、渲染或测试，实际节奏由用户体验。
