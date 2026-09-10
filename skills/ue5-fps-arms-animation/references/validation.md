# 候选发布、运行与音画验收

## 证据链

1. 查看当前实际画面和源动作，保存本次改动前路径、时序与散列。候选检查输出必须晚于相应导出文件，避免用上一代报告验收新 FBX。
2. 按修改范围采样手/弹匣/枪体表面、握持相对矩阵、骨长及关键机械行程。比较已有接触与新穿模，不把探针误差降低等同于自然手型。
3. 导入单个目标 clip，指定兼容 Skeleton 和采样参数；独立读回保存后的压缩动画，比较 raw/compressed 及持握区间偏移。当前 M4 使用 `/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel`。
4. 更新当前 C++/数据的实际引用，必要时编译。以新进程的 `M4_ANIMATION_AUDIT_ACTIVE` 路径和实际输入运行证明已应用；打开的编辑器可能缓存旧模块/资产。
5. 用同一次游戏进程的画面与混音检查音效触发、接触和恢复。不要用导入成功、日志出现 sound 名、静音图片或事后逐事件重配音作同步证据。

阈值按网格尺度、接触余量和本次目标制定。当前 M4 的 480 Hz 导出、960 Hz 骨骼读回、120 Hz 表面探针是解决已观察到的插值误差后的选择，不是所有动画必须套用的成本。

## 单一时钟与机械声音

保持源动画时间、运行时间和 clip 播放率的明确映射：`play_rate = source_duration / gameplay_duration`。分段重定时则音效使用同一映射，不仅缩短状态计时器。

当前 `ReloadSourceTime(WeaponStateElapsed)` 与机械 cue 共用时钟；跨过事件后只触发一次，并在取消/完成时清理事件状态。额外检查重复 R、低帧率、最后一发按住扳机及切枪。

历史故障是 `lateness < sound_duration` 会丢弃比一帧延迟更短的压实声。当前普通 M4 允许尚未过期的接触音播放至下一接触事件或动作结束；迟到跨越多事件时跳过已失效旧音，防止一次补播整串。该修正仅在当前已验证分支生效，别把音效迟到规则未经检查套给弹鼓。

实际 WAV 可与许可明确的来源片段做相关匹配，结合 cue 日志和关键帧判断：是否真的播放、是否错片段、是否截断/削波、是否明显滞后。录音起点、混音缓冲和截图频率会引入偏移，应明确记录。全程时间轴只做统一起点对齐，不逐事件挪音来掩盖游戏不同步。

## 本机复用入口

工作目录选择新候选；以下路径均是案例，先检查存在与脚本所写目的地：

```powershell
$caseDir = 'D:/FPS3D/FPSGAME/SourceAssets/M4TacticalToss20260910'
rg -n 'M4_ANIMATION_AUDIT_ACTIVE|M4TacticalToss|M4SlapImpact|M4WrapGrip' 'D:/FPS3D/FPSGAME/Source/FPSGAME/FPSGAMECharacter.cpp'
# 用全新 Label；脚本拒绝复用已有输出目录，隔离玩家存档。
& "$caseDir/run_validation.ps1" -Fps 60 -Label m4-new-unique-label -CaptureFrames -CaptureAudio -CaptureHz 20 -PreviewWidth 640
```

- `verify_contract.py`：源动作的握持/骨长/机械时间；抓握区间必须随动作更新，不能继续用旧 23–98 断言普通新动作。
- `triangle_contact_probe.py`、`probe_body.py`：指定网格、动作和采样段的表面检查；网格重拓扑后需重新定义采样组。
- `publish.py`：只导入候选目标，先检查报告新鲜度和姿态；脚本有资产写操作，不能不改 destination 就拿来做探索。
- `verify_assets.py`、`verify_mat_saved.py`：独立进程读回 AnimSequence 与 MAT Sequence。
- `check_audio.py <Label>`：检查同次混音和日志；使用已确认音频来源，并核对脚本依赖与预期事件数，不能无条件要求所有测试都恰好 11 音。
- `make_delivery.py`：实际画面与混音对齐；修改 label、采样率、起点及片段时长；如缺截图沿用上一帧，需在清单说明。

UE 命令行位于 `E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/`，Blender 为 `E:/Program Files/Blender Foundation/Blender 5.1/blender.exe`。用 PowerShell 字面路径，Python 使用 `-X utf8`。脚本路径是本机工作入口，不是可发布资产依赖。

## 编译和辅助进程

- 无 Git 的宿主备份精确文件，写入前核对原字节未被并行任务修改。模块使用尚未占用的唯一 `-ModuleWithSuffix=FPSGAME,<suffix>`；不恢复旧 UnrealEditor.modules 来覆盖另一任务构建。
- 查明持有 DLL 的编辑器归属，不反复关闭用户/其他任务的实例。新建自己的隐藏辅助进程；有已打开用户编辑器时明确区分新测试进程已验证与用户编辑器是否已重新加载。
- 实际混音录制时避免同时运行 Blender 渲染、MAT 烘焙或其他重 UE 检查，减少截图遗漏和事件延迟。仍要报告实际缺图。
- commandlet 的既有 GameFeatureData 或 MCP 端口报错与动画检查分开判断。保留退出码、错误和明确产物读回证据；新错误不能一律列为“已有”。MAT 保存后的已知 Sequencer 退出问题见 [MAT 实操](mat-editing.md)。
- 不修改运行时的动画任务，只更新技能/文档时，检查前置元数据、链接、镜像和变更边界即可；不要为文档再跑 50 项游戏审计。
