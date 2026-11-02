# 符文双手剑转刀检视 V85/R6：逆时针起手、掌心托剑与手背回握

2026-11-02。本批公开 [V85/R6](https://github.com/allang2208/3D-FPS) 转刀检视的最终作者源、检视音效与镜头代码，以及配套文档与技能沉淀。L 键播放正式版（R6b，1.158 s，与原始 V82 同长），M 键的临时对比钩子已在正式落盘时移除。用户结论：「基本达标」。

## 动作设计

参考 [BV1hCJFzQEyR](https://www.bilibili.com/video/BV1hCJFzQEyR/) `#10 绕手`（文件 76.00–76.30 s）倒放成逆时针起手。完整转刀由三段组成，按剑的转角对齐拼接：

| 段落 | 片段时间 | 来源 |
| --- | --- | --- |
| 准备、反向预备、松拳甩出 | 0–0.49 s | V85 手势 |
| 手翻成掌心向上、五指张开，剑柄立在掌心滑转 | 约 0.50–0.70 s | V82 掌心托剑 |
| 手翻到剑柄上方、手背握柄，推剑回拳并握死 | 约 0.70–0.82 s | V85 手势 |
| 接刀随动与回收 | 0.82–1.158 s | V85 / V82 同源收尾 |

- 时长 1.158 s（139 个 120 Hz 帧间隔），起手、转刀、收尾三个时间点与 V82 一致；R6b 用一条平滑单调的时间映射把 R6 设计整体压到这张时间表上，各拍在转刀中的占比不变。
- 剑在画面上的转速：甩出峰值约 2155°/s（V82 约 2000°/s），掌心段到手背段最低约 520°/s，推剑约 1080°/s；无停顿、无倒转、逐帧无跳变。
- 交接以手为先：手的位置沿用 V85，朝向在两者间做帧间连续的球面插值，再用 V85 的手臂求解器重解肘肩；剑的转动只来自一条混合时钟。按骨骼局部旋转直接混合会让手一帧甩出 9 m/s，已弃用。

## 直接进入运行树的内容

- `SourceAssets/RuneSword20260913/InspectReverseV85/`：R6 作者脚本（`author_inspect_r6.py`）、V85 求解器、关键帧 `keys_v85.json`、V82 姿势烘焙脚本、节奏测量与预览工具、README。
- `Source/FPSGAME/Weapons/RuneSwordInspectFeel.h`：检视音效路径、音量音高与镜头曲线（`Tempo = 1`，`Motion` 直接写片段时间）。
- `Docs/Weapons/runesword-inspect-v85-20261031.md`：R2–R6b 的完整制作记录；`runesword-inspect-v84-20261031.md`、`runesword-inspect-wrap-plan-20261030.md` 保留为已撤回版本与方案记录。
- `Docs/Weapons/runesword-inspect-v82-20260926.md`：补入 V84/V85 的替换与回退说明。
- `skills/ue5-fps-arms-animation/references/two-handed-melee.md`：新增 V84 撤回、V85 倒放还原、R3/R4 节奏教训、R6 两版拼接、长柄档案重烘共六个条目。
- `.gitignore`：`InspectReverseV85` 的公开白名单（脚本、JSON 键与回执、文档；blend/FBX/预览/回滚包留在本机）。

## 共享宿主差量（Integration/，2 份补丁）

**此提交不是完整本机工程的可构建检出。** `RuneSwordComponent.cpp`、`RuneSwordComponent.h` 在本机工作区同时承载其他会话未发布的改动（`LightningHaste` 攻速、StarMarrow/Beiwei 引用、蓄力重构、护手写时复制等），因此只发布本批的按 HEAD 对齐差量：

- `Integration/Source__FPSGAME__Weapons__RuneSwordComponent.cpp.patch`：`RuneSwordInspectFeel.h` 引用；三件检视音效加载；`BeginInspect` 清四个 cue 标志；`GetCameraMotion` 的 `bInspecting` 分支；`bInspecting` tick 中的四段 cue 播放。
- `Integration/Source__FPSGAME__Weapons__RuneSwordComponent.h.patch`：三个音效成员与四个 cue 标志。
- `integration-prerequisites.json` 给出两份的前置/结果 SHA-256（LF、UTF-8）与语义依赖。前置哈希不符时按语义合并，不要整文件覆盖。

## 运行效果与验证边界

- 本机两套正式 Inspect 已由 commandlet 导入保存：普通柄 `4c7228e5…`→`34dede2d…`，长柄 `3d045200…`→`cb9f8932…`，1.158 s（139 帧）。
- 长柄档案 `DA_Sword_LongGrip` 的 Inspect 条目已按新两套资产重烘（`471d3ffb…`→`ac702f2c…`），否则长柄会用 V82 时间轴的左臂修正。
- `FPSGAMEEditor` 于 2026-11-02 18:03 构建成功（`Saved/BuildEditor/build-20261102-175527.log`）。打包版 Game 目标没有单独构建。
- 没有运行游戏或实机验收；用户试玩结论「基本达标」为本批正式落盘依据。
- 已知残留（作者源指标）：松拳 0.55–0.575 s 柄尾嵌入前臂 17–38 mm、推剑 1.017–1.033 s 护手嵌入前臂 8–11 mm；V82 掌形段护手离掌心 22–27 mm，与 V82 原动画同级。

## 归档

V84 作者目录（已撤回）、V85 的 R2–R6 迭代预览与 7 份旧导入日志、M 键对比钩子脚本共 1682 个文件、1354754307 字节，移入本机 `trash/runesword-inspect-v85-20261102/`，逐文件记录原路径、目标、大小、SHA-256、原因与替代物。见 [归档摘要](archive-summary.json)。`trash/` 不入库。

## 恢复依赖

- 作者需要合法的本机双手剑资产与 `RuneSwordWristLocked20260920/<variant>/Sword_Idle_WristLockedV4.blend` 待机；R6 拼接还需要 V82 作者 Blend 与 `extract_v82_poses.py` 生成的 `Work/v82_poses_*.npz`。
- 检视音效来自 `/Game/FreeGameSoundsVol1/` 与 `/Game/Audio/` 的现有素材，路径写在 `RuneSwordInspectFeel.h`；公开库不含 UE 音频包。
- 正式资产 `A_RuneSword_Inspect` 的 uasset 不在公开库；本机回退包在 `InspectReverseV85/BeforeV85/`。
