# 手掌形变与游戏时间修复 — 2026-09-09

项目：`D:/FPS3D/FPSGAME`，UE 5.8.2。对应用户反馈：换弹、上膛时手掌凹陷，以及枪械表现受帧率影响。

**用户后续实测否决：手部仍明显扭曲。本候选没有通过用户视觉验收；下文的截图检查和自动化通过数不代表手部质量通过。停止继续以 WRAD 手工适配为升级路线。** 新核对发现最初迁移漏掉了 Godot 的正式运行时手网格替换，且旧 staging 的动作采样时间与最终 Godot GLB 不同。完整来源与复用边界见 `../OriginalAnimationMigration/README.md`。

## 修复内容

原版 WRAD 适配的掌区受手掌与多节手指骨混合影响；逐骨缩放的静态适配又使掌面和指根映射不连续。手掌凹陷不能靠播放速度或权重归一化解决。

最终使用 `SK_ArmsRepair_anatomy_v3.blend`：掌区采用连续适配，保留厚度；将远端指骨在近端掌区的错误影响转移回近端；重新分配前臂扭转权重；统一拇指横截面轴的方向，并平滑对齐掌区和五个指根的位置。拇指轴修复前的候选曾出现新的三角折叠，已否决，没有导入该候选。

`Integrated/SK_AKM_HandsRepair_Source.blend` 是最终可编辑的完整 AKM/手臂源文件。`integration.json` 验证原有 82 根骨骼的绑定矩阵保持一致。原有十段动画、动作接触顺序、AKM 零件及七个材质保持复用；没有依靠 Blender 的 Preserve Volume 模式掩盖 UE 线性蒙皮结果。原 WRAD CC0 来源及许可证在 `../ArmsReplacement/WRAD_Original/`。

实际默认加载资产：`/Game/Weapons/AKMReplacement/HandsRepair/SK_AKM_HandsRepair`。旧模型和失败候选保留用于对照。`Integrated/ue_import.json` 和独立进程的 `ue_readback.json` 均确认同一骨架和七个正确材质。首次导入遇到 Python 属性访问错误后改用已核实的 `set_editor_property`；正式导入、保存、独立读回成功。命令行的非零退出仍包含原有 GameFeatureData 配置错误，不能把该退出码单独当作资产成功证据。

## 时间机制

- 普通游戏使用 UE 世界时间，帧数只是离散采样。普通换弹仍为 2.7 秒，空仓换弹 3.466667 秒；ADS 全程进入 240 ms、退出 180 ms。
- ADS 在真实输入或状态变化时登记起点，反向切换先计算旧方向到当前时刻的进度。换弹、装备和冲刺开火锁也使用绝对世界时间，避免新动作吃掉输入发生前的 delta。
- 连射修复了每帧最多一发和超过两次间隔直接丢弃欠账的问题。按时间补足合法射击事件，每批最多四发；换弹、装备、滑铲、冲刺期间不积累非法欠账。补发使用当前帧视角，未重建历史瞄准。
- 烟尘采用解析阻力积分；弹壳子步消耗完整 delta，包括碰撞后余时。余烟保留周期余数，按历史出生时间初始化粒子；当前开火热量不回填到过去。
- 保留 UE 默认世界时间保护：`MaxUndilatedFrameTime=0.4`。超过 400 ms 的严重停顿可能让游戏时间落后墙钟；暂停/时间缩放也不等同于墙钟。本次没有改变全局世界时钟或物理设置。若项目以后提高该上限，连射超出四发批量的历史仍受明确上限限制。

## 验证与证据

- `build-ads-clock.log`：最终原生 Editor 模块编译和链接成功。
- `fire-clock-validation.log`：69 项数学检查通过；30/60/144 Hz、180/400 ms 步长和 200 ms 卡顿下射击数量一致，包括换弹和阻挡边界。
- `verify_fx_time_invariance.py`：66 项数学检查通过，含 200 ms 卡顿。数学检查不替代 UE 渲染和碰撞验收。
- `Saved/GunplayUpgrade/time-repair-realtime`：最初不截图的正常时间复测 42/42；它没有发现后来的单帧单发缺陷。
- `Saved/GunplayUpgrade/hands-repair-v3`：正常时间 + 连续截图，40/42。该失败暴露了卡顿下连射减少，以及测试把迟到的冲刺采样错当作提前开火；两者随后分别修复。没有通过降低预期射速掩盖失败。
- `Saved/GunplayUpgrade/hands-time-final`：正常时间 + 连续截图 + 真实 200 ms 停顿，42/42，明确完成标记、进程退出 0，`fixed_step=0`。这是 ADS 起点修正前最后一轮；手部与射击修复相同。
- 最终 ADS 起点修正后的 `Saved/GunplayUpgrade/hands-ads-time-final/`：正常时间 + 连续截图 + 200 ms 真实停顿，42/42、零失败、退出 0；`fixed_step=0`，连射段实测 8 发。对齐起点后的游戏秒为 29.4545、墙钟秒为 29.6694；保留上述世界时钟上限，未声称墙钟严格一比一。运行脚本要求非零通过数、零失败和显式完成标记。

`root_v3_*.png` 为相同骨骼姿态和相同镜位的无遮挡 A/B。UE 实际画面的 ADS、插匣、抬手和恢复姿态未再见原先的大块掌心塌陷、三角折叠和虎口折带。`ue_hand_review_final.png` 是原游戏截图裁切的动作序列。

**保留的视觉限制：** 无遮挡的极近景在 idle 右拇指根和空仓 52 左拇指根仍存在小夹缝/薄折痕，不能称整手全部无自交。当前实际游戏采样未见这些问题扩大为大块掌心塌陷。10 Hz 截图预览不能排除采样之间的短暂闪烁，也不是人工操作验收。这个 CC0 手臂仍是圆润的风格化模型。

`Preview/` 保留 ADS 起点修正前的手部预览；`PreviewFinal/` 为最终实际游戏预览：119 张源截图组成 142 张、14.2 秒的 MP4/GIF，23 个缺失采样保持上一张。预览按每游戏秒十次截图导出，未加速动作；它不代表游戏渲染帧率。

## 复现入口

工具目录 `Tools/AssetPipeline/`：`repair_arms_skinning.py --variant anatomy_v3`、`root_render_palms.py`、`integrate_repaired_hands.py`、`import_repaired_hands_ue.py`。正式源模型不被这些候选脚本覆盖。

正常时间验收：`run_gunplay_acceptance.ps1 -RealTime -HitchMs 200 -CaptureFrames -Label <new-label>`。注入停顿仅在显式验收参数启用，普通游戏不会注入停顿或固定时间步长。
