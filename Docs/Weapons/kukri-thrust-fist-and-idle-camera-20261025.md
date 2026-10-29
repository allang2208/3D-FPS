# 弯刀第三刺左拳与第一人称待机镜头

用户范围：先修第三刺左手握拳，以及第一人称待机镜头随第三人称呼吸起伏的问题；本轮不制作上挑。

## 修改

- `FPSPlayerFirstPersonBody.cpp::ApplyOwnerCameraOffset` 原先每帧从已经播放动画的骨盆、脊柱、颈部取位置，再推开第一人称相机。呼吸或重心变化会改变这个避让偏移。代码中这条耦合改变的是相机前后避让量，并非头骨直接写入相机 Z。静止、地面、无动作时改用本体参考骨架与视线俯仰构造稳定的躯干包络；保留相机碰撞、原有插值和共用近战眼点。身体仍正常播放呼吸。移动、攻击和其它动作继续使用原有姿态避让。
- 第三人称 `Kukri.FullBody.Thrust` 仅改 Jason、Kaitlin 的左手指骨及其原生辅助骨。复用当前空手/法杖闭拳源的掌面语义、五指弯曲和拇指对握，按各自骨轴转换，保留各自骨长和蒙皮。
- 四指依次收拢，拇指稍后贴合；作者时钟约 0.215 秒完成握拳，0.68 秒开始松开，1.08 秒恢复原姿态。首末帧、右臂刀路、左腕路径、身体脚步、Contact/Release 标记和攻击时长沿用 Combo V3。
- 两个新动画包位于现有 Cook 目录下的 `Animations/ThrustFistV4/`。本地共享配置只替换两个人物的 `Kukri.FullBody.Thrust`，使用 `config_transaction.py`。

## 可编辑源

- `SourceAssets/KukriThrustHand20261025/author.py`：从 Combo V3 第三刺生成两个修订动作。
- `SourceAssets/UnarmedIdle20261001/full-pose.json`：闭拳参考；其上游为 `StaffQuickCombat20261001/FixV2/fist-profile-v2.json`。
- `SourceAssets/KukriThrustHand20261025/save_assets.py`、`publish.py`：新包保存和精确角色接入。
- 原先在正在游玩的编辑器中尝试保存 `A_KukriCombo_ThrustFistV4` 被 UE 拒绝。该未保存草稿不作为交付资产，后台另用新包路径，避免覆盖编辑器里的对象。

## 交付边界

本轮不运行游戏、不截图、不渲染、不做视觉验收。资产保存、配置接入、编译结果分别以作者目录中的回执为准。视觉效果由用户体验；上轮 Combo V3 的构建回执不替代本轮结果。

2026-10-25 当前回执：

- 两个新包后台保存完成，commandlet 退出码 0；两条第三人称突刺配置已接入。
- Game 正式构建成功，编译 `FPSPlayerFirstPersonBody.cpp` 并链接 `FPSGAME.exe`。
- 最初运行编辑器返回 `CompileNotStarted / Live coding canceled`。用户随后选择保存并关闭 UE；关闭后 Editor 正式构建成功，完成 438 个构建任务并链接 `UnrealEditor-FPSGAME.dll`，总耗时 441.77 秒。镜头修复已进入正式模块，无待完成的 Editor 编译。
- 本轮没有重新启动 UE 或游戏，也没有视觉实测。重新打开 UE 后由用户体验。
