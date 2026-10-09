# Super90 快速装填重做 R3

> 2026-10-08：本版已被用户否定，反馈为手臂扭曲/离屏及装填器不可见，不得作为已认可动作。后续修复见 `../Super90LoaderRepair20261008/README.md`；下方保留本版制作和导入历史。

2026-10-07 制作，2026-10-08 00:01（北京时间）后台导入保存完成。按快速装填研究定稿制作，参考 BV11wTe6sEsS 的 40.633–42.50 秒可见动作。作者源、FBX、四类握把差量和可编辑 Blend 已完成，正式 20 项资产全部落盘。`import_receipt.json` 为 `completed=true`，后台 commandlet 正常退出；未打开交互编辑器，未运行游戏测试或验收渲染。

## 本次制作

- 将 UE SOURCE 的根空间校准到原生 Blender 作者空间，去除握把姿态进入装填动作时携带的 0.01 缩放；不改原生 Skeleton、手臂网格或枪体比例。
- 使用 V7 原生手部表面拟合推杆的圆角条、凸起及握柄纹路。保留原生指节平移、骨段长度和轴向滚转，只拟合整手位置、朝向和各指屈伸；由 `handle_grasp.json` 驱动动作和道具绑定。
- 推杆重新绑定到 `hand_l`，管体仍由 `WPN_Shell` 驱动；同步导出 `SK_Super90_LoaderProps.fbx`，不再保留旧的反向 100 倍绑定补偿。
- 左臂采用连续运输的肘极、上下臂共用的解剖铰链；松手后渐进回到原生解剖滚转。前臂蒙皮旋转按本骨架实际 0、1/3、2/3 站点分配。
- 五指分别控制松开、离屏握取和回握时钟；可见退件期间保持握柄，离屏后再张掌。先到达枪体支撑点，再依次合拢各指。
- 空仓增加独立释放钮接触姿态：以实际拇指皮肤接触点求手腕位置，其他手指保持软张状态。空仓释放动作属于本游戏适配，参考视频没有展示这一步。
- 共生成普通 1–7 发、空仓 1–7 发及单独空仓循环共 15 段；四类前握把只适配入场/回握，中间操作阶段共用同一接触动作。数量变体维持共同前缀，兼容现有中断退件逻辑。

## 接入范围

正式资产已保存 20 项：`/Game/Weapons/Super90/Speedloader20261007/SK_Super90_LoaderProps`、同目录 `Animations` 下 15 段装填动作，以及 `Foregrips20261007/Profiles` 下四份握把配置。

`import_rebuild.py` 合并现有配置，只替换装填条目，保留当前冲刺及原有动作和 Retained 引用。材质沿用当前道具材质，枪体、导向件、贴图、音效、图标、瞄具和枪匠数据不需要重做。本次没有 C++ 改动，不需要重编译原生模块。

原时钟继续使用 60 Hz 作者帧：第一发 90 帧，后续每 4 帧；道具 74 帧出现、最后一发后 13 帧隐藏；普通收尾 32 帧、空仓收尾 68 帧，释放钮事件在最后一发后 44 帧。默认播放速度保持 1.3 倍，完整七发普通装填约 1.87 秒。

## 文件与复作

1. `read_grasp_source.py` 从本次归档的旧作者输入及原生 V7 网格提取接触制作输入；Blender 后台执行。
2. `fit_handle_grasp.py` 用本地 Python + NumPy/SciPy 生成 `handle_grasp.json`；这是制作拟合，不是画面验收。
3. 正式作者源为 `../Super90Speedloader20261007/author_speedloader.py`；Blender 后台执行后生成该目录 `Exports`、四份 `*_profiles.json` 和作者清单。
4. 可编辑工程：`Super90_Speedloader_RebuildR3.blend`。原生产目录的 `Super90_Speedloader_Editable.blend` 同步更新，历史 ReferenceR2 工程不覆盖。
5. 导入入口为本目录 `import_rebuild.py`；编辑器已运行时走 `Tools/AssetPipeline/mcp_call_codex.ps1` 的批次互斥，未运行时可用 `../Super90SprintArmR3_20261007/run_background.ps1` 执行后台 commandlet。不得在 PIE 中覆盖资产。
6. `import_receipt.json` 记录实际保存进度；只有 `completed=true` 才代表本批 20 项资产全部落盘。`Before/Source` 保留旧作者源、动画、握把差量和 Blend；`Before/Content` 在导入前备份本批正式资产。

研究来源见 `../Super90AAnimStudy20261007/RESEARCH_RESULT.md`。AAnim 只用于分指/阶段结构学习，没有直接迁移其 RTM、猜测源绑定或声称复现遮挡部分。当前动作需由用户在游戏中判断抓握、腕肘、取件、推进和收势效果；本次未进行自测。
