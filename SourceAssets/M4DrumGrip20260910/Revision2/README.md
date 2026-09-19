# M4 大弹鼓换弹重制 — 2026-09-10

> 后续左腕/前臂细修见 `../Revision3/README.md`。当前同名正式动画已更新为 Revision3 的 120 Hz 版本；本文及 `default_final_*` 保留整体动作重制阶段的记录。

已接为默认大弹鼓换弹，资源目录 `/Game/Weapons/M4DrumGripRebuilt`。正常启动无需候选参数。保留现有 M4、Manny 手臂和大弹鼓模型；标准弹匣继续读取其他任务维护的 `M4ContactImpactFinal`。

## 修正

- 重做张手、拇指与四指对向包握、取出、持鼓回送、对准、插入、坐实、松手回位；不再沿用细弹匣离屏瞬移的路径。
- 手指按屈伸轴和受限拇指外展拟合，前臂扭转分配给辅助骨骼，左臂保持骨长。右肩有受控的下沉，避免前移的视角模型把上臂截断端带入相机近裁切面。
- 起止姿态与大弹鼓专用待机姿态衔接。左手支撑点比当前标准弹匣再向护木前移 20 mm；待机、瞄准、射击、瞄准射击、装备的专用副本只在安装大弹鼓时使用。
- 空仓插入后直接退手并伸出食指触及机匣释放钮，消除先甩开又回到弹鼓的多余折返。
- 保留源动画 2.1 / 2.7 秒与原有游戏播放时序、音效时钟、50 发容量和弹药事务。

## 查看与编辑

- `default_final_normal.gif`、`default_final_empty.gif`：本次正式引用的真实游戏截图动图，使用每张截图记录的游戏时间；81 / 103 帧，约 22–30 张截图/秒，无音频。不是 60 fps 视频或性能测试。
- `default_final_*_sheet0.jpg` / `sheet1.jpg`：覆盖整段动作的接触表。
- `M4_DrumGrip_Rebuilt.blend`：包含现有手臂、枪械、弹鼓及两套新动作的可编辑源。动作名 `A_M4_DrumGrip_reload` / `A_M4_DrumGrip_reload_empty`。
- 同名 FBX：最终导入文件。`rebuild_motion.py`、`fit_anatomical_grip.py` 和 `anatomical_grip.json` 可复现制作。
- `Frames/`、`study_*`、`grip_*`、`rebuilt_r2*` 是过程证据，部分早于最终修正；正式结果以 `default_final_*` 和当前 Blend/FBX 为准。

本次完成 Blender 动作重制、UE 动画导入和游戏接入。旧目录中的 MAT/Sequencer 实验未在本次发布为已验证的编辑工作流。

## 验证与范围

- C++ 编译：`build57.log` 成功。正式启动不带候选参数：`runtime-default_final.log`，`DRUM_GRIP: COMPLETE failures=0`。检查默认资源路径、五套支撑动画时长、普通/空仓换弹、50 发填充、弹药账目和弹鼓挂接位置/旋转/缩放。
- 真实游戏复查发现并修正右上臂穿过相机产生的长弧。判断包含正常/空仓全程接触表及抓握、插入、释放钮、起止姿态截图；不是仅依据日志通过。
- `full_motion_contact.json`：两套动作全部整数帧的左掌/手指皮肤顶点与鼓体圆柱包络检查，最大残余侵入约 0.29 mm，没有超过 1 mm 的顶点。此项没有覆盖所有枪械表面、手部自碰撞或所有游戏姿态。
- `continuity_report.json`：120 Hz 采样检查关节旋转、位置、局部平移和缩放。不存在旧版单帧 110° 的腕部跳变；起手仍是较快的姿态过渡，具体观感以动图为准。
- `release_contact.json`：空仓第 130 帧实际食指皮肤接触点与目标误差小于 0.001 mm；目标取自项目现有 M4 释放钮。
- `import_report.json`：127 / 163 个采样帧，压缩误差最大约 0.0029 cm。导入命令行受项目现有 GameFeatureData 配置错误影响返回非零，Python 保存、长度和压缩检查成功；另一个新游戏进程已确认正式资源加载和运行。

当前已打开的 UE 编辑器需要保存工作并重启才能加载新 C++ 模块；本次未关闭或替用户保存编辑器。独立测试使用专用审计存档。

## 重跑

Blender 后台运行 `rebuild_motion.py -- --no-render`；运行 `check_contact.py`、`check_motion.py`、`check_press_contact.py`。UE Python 命令运行 `import_rebuilt.py`，编译项目后运行 `run_review.ps1 -Run 新标签 -DefaultAssets`，再运行 `make_review.py 新标签` 生成实机动图。不要用本目录上层旧候选测试作为新版验收。
