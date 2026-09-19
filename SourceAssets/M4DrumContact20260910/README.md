# M4 大弹鼓插入接触修正

当前默认动画为 `/Game/Weapons/M4DrumDrop/Contact/A_M4_DrumContact_reload` 和 `A_M4_DrumContact_reload_empty`。源动作来自 `../M4DrumGrip20260910/Revision7/M4_DrumMatch_Editable.blend`；模型、手套、材质、许可来源沿用原项目，没有新增外部素材。

普通动作在源帧 69–75、空仓在 47–53 提前平滑对正连接颈，之后沿弹匣井轴线推进。保留原轴向深度、普通第 95 帧/空仓第 80 帧压实，以及空仓第 116 帧拍击。总源时长仍为 2.1 秒和 148/60 秒，运行时仍为 3.110374 秒和 3.861572 秒。`M4DrumReloadTiming.h` 和声音事件未改。

左手刚性跟随弹鼓；肩部固定、双骨 IK 调整肘部，保持上臂和前臂长度。手掌最多移动约 1.74/2.33 厘米，肘部约 1.85/2.54 厘米。手指局部握持与右手/枪根动作保留。

## 文件

- [可编辑 Blender 源](M4_DrumContact_Editable.blend)
- [普通换弹 FBX](A_M4_DrumContact_reload.fbx)、[空仓换弹 FBX](A_M4_DrumContact_reload_empty.fbx)
- [实际游戏及同次混音视频](Delivery/M4_drum_reload_with_game_audio.mp4)
- [普通动作 GIF](normal_preview.gif)、[空仓动作 GIF](empty_preview.gif)
- [验收记录](acceptance.json)、[独立保存后读回](saved_validation.json)

## 验证与复现

`author_contact.py` 生成独立动作、240 Hz FBX 与 Blend；`verify_contact.py` 每四分之一源帧检查弹鼓/枪体三角相交。比较完全插稳姿态的接触集合，修复前瞬态新增枪体交叉面峰值为普通 25、空仓 31，修复后为 0。该指标排除模型装配部位原有重叠，不代表整个模型所有表面绝对零交叉。

`import_contact.py` 导入独立 UE 路径并以 960 Hz 检查 RAW/COMPRESSED 骨骼差异；`verify_saved.py` 在另一个 UE 进程重新读取保存后的压缩资产，直线插入段分别检查 321/433 个点，侧向误差均小于 0.005 cm。

Editor Development 编译通过，`drum-contact-v2` 新游戏进程实际加载 `UnrealEditor-FPSGAME-2247.dll` 和 Contact 动画，172 PASS、0 FAIL。检查两种换弹、50 发结算、掉鼓、挂接和既有时序。140 张实际截图制作 7.808 秒视频，截图间保持前帧；同次混音检出全部 7 个机械事件，波形相关性均大于 0.99，无削波。已检查普通与空仓接触连续截图。

首轮 `drum-contact-v1` 高分辨率录制遇到帧卡顿并漏播一个短事件，未作为最终音画通过证据；保留日志。最终 `v2` 使用 640×360 录制，未修改原声音处理逻辑。

复跑：`run_review.ps1 -Run <唯一名称> -DefaultAssets`，随后 `python make_delivery.py <同一名称>`。测试使用独立 `DrumGripAudit_...` 存档。用户原有编辑器未被关闭，需重新启动以加载新的原生模块。
