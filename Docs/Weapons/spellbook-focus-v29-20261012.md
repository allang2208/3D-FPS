# 魔法书 V29：开书与收书 2 倍速

后续张合手自然度细调见 [V30 手指、整臂与回握衔接](spellbook-focus-v30-20261012.md)。V29 的 1.12 秒时长继续保留。

用户要求在 V28 基础上将开书与收书的播放速度提升一倍。

- 两个完整动作均由 2.24 秒缩短为 1.12 秒；原 0.20 秒握持停顿同比缩短为 0.10 秒。
- 只缩放共享播放时间轴，保持原手势、书本方向、轨迹、先翻转后张掌的顺序和非线性速度曲线。中途取消仍从当前进度倒放。
- 收书时托掌晃动的渐退同步加速，以便在回握前收住。阅读状态的托掌晃动、浮动频率和 16 秒翻页周期不变。
- 继续复用 FocusV27 动画资产；活动制作入口转入 `IntegratedV29/save_editable.py`，可编辑开书/收书 Blend 同步保存新时序。

源码与制作记录位于 `SourceAssets/SpellbookEvildeer20261009/Focus/IntegratedV29/`。编译应用状态以该目录的 `delivery.json` 为准。没有启动 UE、游戏或追加测试。

## 已保存与构建状态

- 后台 Blender 已保存活动源 `Focus/Spellbook_Focus.blend`、`Focus/Spellbook_Recover.blend`；`editable-source.json` 记录 revision 29、播放倍率 2.0、完整开合 1.12 秒和握持停顿 0.10 秒。保存日志为 `IntegratedV29/editable-console.log`。
- 2026-10-12 09:09:04（北京时间），当时已有的编辑器完成 Live Coding，日志记录 `Live coding succeeded`。
- 编辑器退出后，正式后台 `FPSGAMEEditor Win64 Development` 构建于 09:12 完成，结果 `Succeeded`，耗时 47.57 秒，并重新链接基础 `UnrealEditor-FPSGAME.dll`。日志为 `Saved/BuildEditor/build-spellbook-v29-20261012.log` 和 `IntegratedV29/build-console.log`；此改动已写入正式构建，不再仅依赖热更新补丁。
- 本版通过 C++ 共享时钟采样已有 FocusV27 动画，不需要重新导入动画资产。

原对话在构建完成后连续发生回复流断线，未写完交付回执。接续对话补齐 `IntegratedV29/delivery.json` 及本节，沿用已保存源码、可编辑源和已有成功构建结果，没有重复构建、启动编辑器或追加游戏测试。2 倍速的视觉效果与操作手感仍由用户测试。
