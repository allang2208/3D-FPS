# 法杖释放右臂重建 · 2026-10-01

用户在新积蓄修订后再次指出：释放时右手上臂、肘关节仍然扭曲，并提供了持杖截图。本次修正对象是积蓄结束后的释放与收势，不能把此前仅修积蓄的交付当作整套施法动作已经成立。

## 根因与替换范围

积蓄末端使用 `ChargeFlow20261001` 修订 `2026100102` 的 `RaisedSettled`，释放下一帧却切回 `CastElbowRepair20260930` 的旧 Raised、Windup、Release、Follow。两套肩肘支撑及辅助骨处理不同：旧切换造成肩位置相差约 24.3 cm、肘位置相差约 17.3 cm。手掌和法杖的握点接近，并不能保证握点背后的完整右臂连续。

旧 Release 的前臂骨方向偏离原生肘铰链平面约 62.8°，Follow 约 68.9°；合金握柄对应约 61°、67°。旧方案固定部分辅助骨的组件空间端点，再通过局部补偿追随手腕，会继续改变骨段轴向关系。这是动作源和混合逻辑的问题，不能用衣袖遮挡或保留骨长替代修复。

新基础表 `StaffAuthoredReleaseAnatomy20261001.h` 对应作者目录 `SourceAssets/ApprenticeStaff20260927/ReleaseAnatomy20261001/`，包含四握柄的 `Idle / Raised / Windup / Release / Follow / Run` 六个完整姿态。Idle 与 Run 原样保留；Raised 的完整右链直接复制当前积蓄终点。旧 `CastElbowRepair20260930` 继续保留为抓握与历史输入，不再作为当前释放右臂的动作表。

## 右臂制作与运行

Windup、Release、Follow 从肩锚点、实际握掌和原生两骨长度重新解算。当前 rig 上臂长约 27.7707 cm、前臂长约 27.2510 cm；肘在原生骨长的肘圆上求支撑点，pole 先从当前握掌与 carry 腕姿反推前臂方向，再沿该原生肘圆选择同时保持实际腕姿与前一控制上臂方向连续的 swivel。上臂框架使用原生 rest 的弯曲平面，肘只按固定铰链屈伸，前臂 roll 从实际掌宽投影取得并限制在 45°。四根 upper/lower twist 保持所属骨段的完整 rest-local 关系，不再锁住辅助骨端点后反向补偿。

原水平出杖方向直接采用 carry 推导的 pole 会选到反面的弯曲平面，产生约 125° 上臂转动与约 139° 腕部变化。因此 carry 只作为搜索 seed，肘圆的选择代价同时包含腕相对 carry 与上臂相对前一控制的旋转变化；当前相邻上臂控制变化约 4–9°，释放/下压的肘点保持在腕下方。释放接触与下压段仍会有约 42–46° 的腕姿变化，观感由用户测试，本记录不声称该角度已获视觉认可。

相机厘米空间的当前作者肩锚点依次为 Windup `(-9,16,-14)`、Release `(0,16,-14)`、Follow `(-1,16,-14)`。保留四握柄各自原生手指、掌向和手在握点中的变换；握点及杆轴的制作参数以同目录 `authored-parameters.json`、`full-pose.json` 为准。这些参数用于本法杖右手握姿，不作为其他骨架的通用坐标。

`StaffGripPose` 的释放和积蓄分支统一先按动作权重混合肘屈伸与前臂 roll 标量，再组装下臂局部旋转。肩、肘、腕、辅助骨及抓握随后在同一父骨链中求 FK；释放和恢复的 `ContactFromArm` 从该真实右手链生成杖握点，不再独立插值握点并围绕手腕拖动整臂。施法期间停止 carry 的额外肘扰动，缓存同时纳入新释放表和积蓄表的 revision，避免保留旧表结果。

动作时序保留：0.035 秒前置蓄势、0.18 秒接触、0.28 秒前挥、0.10 秒停留、0.42 秒恢复。技能数值、投射物、攻速时钟及四握柄接触不随本次右臂重建改变。提前释放仍从当时完整积蓄姿态接入，恢复从真实离场姿态回到实时 carry。

## 源文件与交付记录

作者目录保存 `author_motion.py`、`full-pose.json`、`authored-parameters.json`、`save_editable.py` 及对应可编辑 Blender 源。运行直接读取编入 C++ 的完整局部姿态表，不需要另行导入 UE AnimSequence；脚本、实际保存源文件和运行构建分别记录。

实际作者源保存、构建产物及当前编辑器生效范围以 `SourceAssets/ApprenticeStaff20260927/ReleaseAnatomy20261001/integration-completion.json` 为准。现有编辑器若通过 Live Coding 应用补丁，与基础 Editor DLL 后台重建是不同交付结果；本文件不预先声明任一构建或生效已完成。

未进行游戏测试、预览、渲染或视觉验收，也未为本任务启动或关闭 UE。新版尚无用户观感认可，由用户在游戏中确认。

必要构建期间修正两处既有编译阻断：`SlagBlackMist::GetLifetimeReplicatedProps` 的 cpp 形参及 Super 调用改用宏要求的 `OutLifetimeProps` 名；`M07InteractingClothingAsset` 的三角索引循环改用同源 `uint32` 计数，消除有符号比较错误。仅改变编译所需名称/类型，原文件备份在 `Saved/StaffReleaseAnatomy20261001/BeforeCompileFix/`，不改变怪物或服饰逻辑。

本轮实际结果：最新 Game 后台构建成功，`FPSGAME.exe` 已落盘；当前编辑器于 2026-10-01 15:05:06 UTC 记录 `CompileLiveCoding: Result: Success`。请求 HTTP 超时后仅依据该批次实际完成日志确认结果。

用户确认退出主工程编辑器后，已执行常规 `FPSGAMEEditor Win64 Development` 后台构建，结果 `Succeeded`。该次 UBT 报告 `Target is up to date`，执行 0 个动作；基础模块已由此前常规构建写入，`Binaries/Win64/UnrealEditor-FPSGAME.dll` 的落盘时间为 2026-10-01 15:11:46.846 UTC。本次增量构建没有重新链接 DLL，日志为 `Saved/StaffReleaseAnatomy20261001/FPSGAMEEditor-build.log`。法杖释放修复已纳入常规 Editor 构建，下次启动可直接使用；本任务未启动、关闭或重启编辑器，未运行游戏测试。
