# M4：HK416 音效迁移与空仓释放 — 2026-09-09

## 输入与动作依据

Godot 项目只读：`E:/3d/3-dfps/weapon_data/hk416.tres`、`scripts/hk416_viewmodel.gd`、`scripts/rifle_reload_audio.gd`、`assets/sfx/hk416/`。当前 HK416 普通/空仓换弹运行时长为 2.1/2.7 秒；音频组件按动画进度触发独立接触音。其 `reload.mp3` 仍在资源配置中，但模型的分段音频接管实际换弹播放。

UE 原始手臂包 `Animations_Assault_Rifle.blend` 有普通 Reload（0–94 帧、30 Hz），没有独立 empty reload/charge。原实现的普通与空仓来自同一 Reload。本次保留普通换弹，新增空仓动作。

已查看 HK416 原模型连续动画的插匣后阶段，输出 `hk_reference_*.png`、`hk_motion.json`：左手离开弹匣，抬至机匣侧面、按压枪机释放钮，再回握护木。该参考是空仓挂机释放，非后方拉柄动作。M4 以自身骨骼与接触位置重新制作这一阶段，未直接复制不兼容骨骼旋转。

## 产物与时序

- `M4_EmptyReload_BoltRelease.blend` / `A_M4_ReloadEmpty_BoltRelease.fbx`：可编辑源和 60 Hz 烘焙，229 帧、3.8 秒；游戏空仓时长继续为 3.466667 秒。
- 源帧 30 拔匣、90 插匣、114 拍匣、180 释放，184 枪机闭合；使用同一动画时间映射触发音效。
- 原普通换弹仍使用 `M4InfimaRigV4/ReloadFinger/A_AKM_reload`，保留右食指自然弯曲。
- `SK_M4_Infima_BoltReceiver.fbx`：保持 98 骨与原层级/材质槽，只将机匣内既有枪机的 612 个顶点重新绑定到现有 `WPN_bolt`，增加 3.5 cm 空仓开闭行程。未新增替代几何。
- `/Game/Weapons/M4EmptyReload/`：新网格与专属空仓片段，复用 RigV4 骨架及原材质。
- 当前并行的折叠照门工作已从本次 `M4_EmptyReload_BoltRelease.blend` 派生 `M4FoldingSights/SK_M4_FoldingSights`，保留枪机顶点权重。最终实机检查加载的是这一派生网格；保留其正式引用，不回退覆盖折叠照门。
- `/Game/Weapons/M4HK416Audio/`：HK416 Fire、MagOut、MagInsert、MagSeat、BoltRelease。
- 开火 MP3 仅解码为 48 kHz PCM WAV；四段机械 WAV 原样复制。开火用单一角色音频组件每发重启，音量 -5 dB、原始音高；机械音 -4 dB。未改装备/干扣/命中声。
- 长卡顿后已过期的机械声不补成一串；同一动作内每个事件只触发一次。普通换弹不会触发空仓释放音。

## 来源记录

音效沿用 `Audio/SOURCE.md` 的项目原记录，原文件复制于 `Audio/`，导入路径和 SHA-256 在 `audio_import.json`。未赋予新的许可。

HK416 动作参考署名沿用源项目 `assets/models/hk416/CREDITS.md`：BURNER (Alexander_Ovelar) — HK 416 A7 FPS ANIMATION；原枪模 r4m；源模型与动画记录为 CC BY 4.0。Infima 手臂及原动作保留其自身许可。源记录随本目录保存。

## 验证与重现

Blender 脚本：`probe_sources.py`、`reference_frames.py`、`probe_body.py`、`build_empty.py`、`render_empty.py`。UE 脚本：`import_audio.py`、`import_empty.py`。导入后检查实际压缩骨骼姿态，输出 `empty_import.json`。

`run_validation.ps1` 使用独立测试存档；`-CaptureAudio -CaptureFrames` 用真实时间更新并导出实际混音器音轨。普通 `-Fps 30/60/144` 是固定模拟频率回归，不是实测 FPS。音轨配合实际截帧生成视频，不用后期猜测的事件音轨冒充实时录音。

备份在 `trash/M4HK416AudioEmpty-before-20260909`。项目存在并行编辑，只撤回本次相关变更，禁止用整份旧文件覆盖新功能。

## 最终结果

- `build-83.log`：UE Editor Development 编译成功。保持正在运行的用户编辑器，验证使用独立游戏进程；现有编辑器需重新加载新模块后才能运行此次代码。
- `Saved/GunplayUpgrade/m4-hk416-final-{30,60,144}`：每组 49 项通过、0 失败、进程正常退出。音效事件最大调度迟延依次为 31.579 / 14.913 / 6.650 毫秒，均小于对应一帧。包括弹药仅结算一次、换弹期间禁止开火、持续扣扳机后的空仓换弹、ADS/奔跑/滑铲组合与原刚性组件稳定性。
- 每次普通换弹 3 个事件，每次空仓 4 个事件；测试中的一次普通与两次空仓共 11 个事件。枪机释放行程实机约 3.50003 cm。
- `empty_import.json`：457 个压缩姿态采样，最大骨骼位置误差 0.000335 cm 以内；`empty_build.json` 记录骨段长度误差及接触阶段。指部姿态沿用已修复的弯曲版本。
- `m4-hk416-av60-audible`：50 项通过，导出 29.483 秒、48 kHz 双声道的实际混音器 WAV。开火起音与 HK416 源音频相关系数 0.99947，11 次机械声相关系数 0.91858–0.99521；峰值 0.67048 以下、无削波。详见 `audio_validation_m4-hk416-av60-audible.json`。
- `Preview/M4_HK416_实际音效与空仓换弹.mp4`：同一次运行的实际截图与实际音轨，14.2 秒、10 Hz 截帧；只做录音起点对齐，不重排或合成事件音。截帧造成运行停顿及音频缓冲延迟，不用该视频推断常规游戏帧率或音频设备延迟。126 张原图补齐为 142 个时间槽，缺失槽保持前一帧；详见 `Preview/preview.json`。
- `Preview/空仓动作关键帧.png`：实际游戏中的插匣、抬手、按压释放与回握。`M4_EmptyReload_BoltRelease.blend` 为可编辑源。

早期日志保留作为排错记录：沙箱缓存权限/Zen 导致的启动失败不计为成功；初始后台录音是静音，已通过验证进程的临时后台音量与保留静音区间设置修正。枪机行程检查改为同一空仓片段内开闭位置比较，避免将持枪动画自带的 0.25 cm 偏置计入释放行程。正式游戏音量与引擎全局配置未改。
