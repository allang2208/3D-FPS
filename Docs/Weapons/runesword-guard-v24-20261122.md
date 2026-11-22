# 双手剑格挡 V24：还原 Kubold 参考 1:49–1:52（2026-11-22）

**正式版（用户 2026-11-22 认可「合格」）**：V24 是双手剑现行格挡，取代 V23。

用户要求参考 YouTube `NTrzxPIXer4`（Kubold FPP Melee Animset · Two Handed Sword）1:49–1:52 做一款新的双手剑格挡，力求还原。V24 取代 V23 张掌格挡（[V23 记录](runesword-guard-v23-20260926.md)），普通柄和长柄各三段：Guard、GuardHit、GuardBreak。

## 动作

- **举起 0.46 s**：剑从待机向右下方倾倒，剑根落在画面左下，剑身 42° 斜向右上伸出画面，护手竖立。横向先到位、纵向后到位，剑身转角先过冲约 9% 再回到位，节奏取自参考 110.94–111.40 s。
- **持守**：一个 2.05 s 的呼吸周期，剑根上下约 40 px、左右约 5 px，运行时循环。
- **受击 0.75 s**（参考 117.64–118.39 s）：剑根被打得上跳，剑身压平向脸前，停顿后回到持守。剑离镜头的距离按参考剑宽估计为持守的 0.74–0.98 倍。
- **破防 0.45 s**（参考 119.70–120.15 s）：剑被打向右下，剑身压到约 12°，保持低位直到 1.5 s 眩晕结束，再用 0.32 s 回待机。参考在这一下之后立刻恢复，没有真正的破防。

## 运行时

`Source/FPSGAME/Weapons/RuneSwordGuard.cpp`、`RuneSwordGuardTuning.h`：

- Guard 片段举起后在片段最后一个呼吸周期内循环；闪电加速只加快举起，呼吸保持参考节奏。
- 受击结束接回持守起点（0.46 s）。按住格挡时受击完整播放；受击中或呼吸中松开，先用 0.12 s 从当前姿势混合到持守起点，再像以前一样用 0.18 s 收起。收起期间仍不能出刀，反击时机不比 V23 晚。
- 剑的持守镜头静态偏移（后退 3 cm、下压 1.8 cm、俯 1.8°）归零，参考镜头不动；受击镜头冲击保留。双手锤的格挡镜头不变。
- 破防眩晕结束后的回待机混合由 0.10 s 改为 0.32 s。
- 不变：格挡减伤、弹反窗口、耐力、破防眩晕、联机校验，以及第三人称身体格挡动作和它的 0.20 s 举起。
- 片段短于 0.46 + 2.05 s 时按旧的举起即持守方式播放，所以旧资产仍能正常工作。

## 与参考的差别

- 参考是细长剑，我们的符文剑剑面 7–10 cm、护手 36 cm。剑放在参考的同一屏幕位置时，剑根旁宽约 171 px，参考为 85 px。再往远放，右臂会伸直，到达极限。
- 刃口朝镜头的方案（r5）能让剑看起来一样细，但举起时护手扫进镜头，左拳要绕柄转约 156°，已否定。
- 破防保持低位，参考是马上恢复。破防 0.05–0.15 s 左前臂扭转从 +5° 摆到 −95° 再到 +90°，这段左手在画面下沿之外。

## 文件

- 作者源与参考读数：[GuardKuboldV24](../../SourceAssets/RuneSword20260913/GuardKuboldV24/README.md)。
- 参考录像：`F:/FPSGAMEData/ArtProduction/SourceAssets/Weapons/RuneSword20260913/Reference/KuboldTwoHandedNTrzxPIXer4/`。
- 参考对比图：`F:/FPSGAMEData/ArtReviews/RuneSword20260913/GuardKuboldV24/20261122-r9/`。
- 安装批次（V23 原包备份、最终 FBX、起手接回键、回执）：`F:/FPSGAMEData/ArtProduction/RuneSword20260913/GuardKuboldV24/Install-20261122/`。

## 状态

- **接入（2026-11-22 21:32）**：后台 commandlet 导入并保存 6 段动画，`GUARD_V24_COMPLETE 6`，0 错误。

  | 资产 | 时长 | SHA-256（前 12 位） |
  | --- | --- | --- |
  | 普通柄 Guard | 0.20 → 2.508 s | `c5d403d5cdd8` → `b05e8c03aef1` |
  | 普通柄 GuardHit | 0.221 → 0.75 s | `f8c712177d70` → `006b0331b82f` |
  | 普通柄 GuardBreak | 0.40 → 0.45 s | `14436e13f494` → `8c3f4977c88f` |
  | 长柄 Guard | 0.20 → 2.508 s | `b9a3b0ca91a9` → `5bd0697556b8` |
  | 长柄 GuardHit | 0.221 → 0.75 s | `02e24b6cb7d6` → `b35a7c906d8d` |
  | 长柄 GuardBreak | 0.40 → 0.45 s | `53093869cff2` → `a9f4f580092b` |

  Guard 起手接回现装待机：两套待机相对作者待机都偏移 (0, 6.0, −1.2) cm，前 4 帧（约 33 ms）有混合。`DA_Sword_LongGrip` 的三个条目都按新资产重烘（`ac702f2c3627` → `be68be250e34`）：Guard 含两臂与剑骨差值，GuardHit、GuardBreak 只有左臂差值。
- **编译**：21:33 FPSGAMEEditor 构建成功（`Saved/BuildEditor/build-20261122-213346.log`），`UnrealEditor-FPSGAME.dll` 生成于 21:34。`RuneSwordGuard.cpp`（20:33 最后修改）已在另一会话 21:15 的构建中编译，目标文件晚于源码和 `RuneSwordGuardTuning.h`，本次构建只重编了其他会话的一个文件并重新链接。
- 用户 2026-11-22 认可「合格」，定为正式双手剑格挡。本次制作没有另跑自动测试。

## 正式落盘（2026-11-22）

- 游戏一直使用原资产路径，V24 接入时已替换 V23，无需改引用。V23 原包与改前长柄档案保留在安装批次的 `Before/` 作恢复依据；V23 作者源 `SourceAssets/SwordGuardPalmPush20260926/` 保留原位，仅标记为已被取代。
- 迭代中间输出（r1–r8 对比图和渲染、参考网格图与追踪叠图、作者日志、两份可重建的预览 blend，共 294 个文件、387 MB）移入 `trash/runesword-guard-v24-20261122/`。逐文件原路径、大小、SHA-256 与原因见 `F:/FPSGAMEData/ArtProduction/RuneSword20260913/GuardKuboldV24/Cleanup-20261122/archive-manifest.json`（移动后已逐个读回校验）。作者目录 `Work/` 只保留 r9 定稿图、被键位引用的 `r5_guard.jpg` 与 `width_probe.png`，以及 `run_round.sh`、`probe_sword.*`。
- Git 尚未提交或推送。
