# ASH-12 单手竖枪战术冲刺（2026-09-19）

## 动作来源与制作

本轮沿用已接入 M4 / AKM / QBZ191 的战术冲刺状态体系，以 ASH-12 当前 `ASH12_idle` 为起止握姿，制作独立进入、循环、退出动画。制作前查看已有真实运行参考 `Saved/RifleSprintAudit/RifleSprintAudit-final60-v2/Preview/M4-grips-transitions.jpg`，并读取现有制作脚本、连续进度和左腕松弛编排。

参考里的分工是右手带枪竖起，左手先脱离、再退到画面外；回落末段才恢复前方支撑握持。本轮是基于 ASH-12 自己的枪身尺寸、肩肘腕位置进行适配，未换用其他步枪的骨架或直接引用其动画。

| 片段 | 时长 | 编排 |
| --- | --- | --- |
| Enter | 0.30 s | 左手先松指，向外下撤；右手随后带整枪抬起 |
| Loop | 0.60 s | 单手竖枪，枪体小幅跟随脚步；左臂在身体侧下方自然轻摆 |
| Exit | 0.30 s | 沿同一路径回落，末段回到 ASH-12 原厂前方支撑握姿 |

- 抬枪轴由本枪枪口与枪根求得，目标向上约 76°；右腕向右 12 cm、向前 9.5 cm、向下 2 cm，给无托机匣后段留出位置。
- 右手、手指及全部 `WPN_` 机械骨使用同一个刚性变换，肩肘和 twist 骨随之求解。
- 左手走肩部为中心的外侧弧线，终点接近自然下垂，手腕按局部关节松弛，手指沿原骨段逐级松开；不隐藏或缩放手臂。
- 左臂以放到画面下方为制作目标；没有执行本轮渲染或视野验收，实际效果交由用户确认。
- 120 Hz 烘焙，60 fps 作者时间轴，分别导出 18 / 36 / 18 帧范围。循环首尾正弦位移为零，接回抬枪终点。

## 状态接入

- `ERifleSprintWeapon` 增加 `ASH12`，角色装备本枪时选择该类型。
- `UM4TacticalSprintComponent` 加载本枪三条专用动画。目前 ASH-12 只开放原厂支撑握姿，组件固定使用 Base，不借用其他枪的握把片段。
- 运行时继续用 Enter 轨迹按同一进度正放／倒放，中途松开或重新按住冲刺从当前位置反向。
- 普通松开回步行为 0.30 秒；开火、ADS 或武器动作退出为 0.16 秒，角色原有 0.18 秒冲刺后开火等待不变。
- 专用动作接管后，现有代码自动退出旧整枪偏移层，并接入同一脚步相位的战术冲刺镜头。保留上轮换弹镜头、开火声、普通及空仓换弹动作。
- 输入仍为持枪前进时持续按住 **W + LeftShift**。松开 Shift 落枪；短按 Shift 仍按现有闪避逻辑处理。
- 原有速度、体力、滑铲、翻越、施法及忙碌状态继续由角色逻辑管理。

## 文件

- 作者入口：[author_sprint.py](../../SourceAssets/ASH12TacticalSprint20260919/author_sprint.py)
- 可编辑源：[ASH12_TacticalSprint_Editable.blend](../../SourceAssets/ASH12TacticalSprint20260919/ASH12_TacticalSprint_Editable.blend)
- FBX：`SourceAssets/ASH12TacticalSprint20260919/Animations/A_ASH12_TacticalSprint_{Enter,Loop,Exit}.fbx`
- 导入入口：[import_sprint.py](../../SourceAssets/ASH12TacticalSprint20260919/import_sprint.py)，使用现有 ASH-12 私有骨架和 `BC_M4Viewmodel` 压缩设置。
- UE 目录：`/Game/Weapons/ASH12/TacticalSprint20260919/`，已加入 `DefaultGame.ini` 的打包保留目录。
- 接入：`ASH12WeaponAssets.h`、`M4TacticalSprintComponent.h/.cpp`、`FPSGAMECharacter.cpp`。

## 交付状态

已完成动作制作、FBX 导出、接入代码，以及三条 UE 动画的导入保存。导入回执：[import.json](../../SourceAssets/ASH12TacticalSprint20260919/import.json)，源时长为 0.30 / 0.60 / 0.30 秒。

导入日志记录 `ASH12_TACTICAL_SPRINT_IMPORT_COMPLETE`、`Python script executed successfully`，三条动画均已保存。命令行整体退出码为 1，唯一错误是并行编辑器已占用 MCP 的 `127.0.0.1:8000`，不是动画导入失败；另有三条源 FBX 绑定姿势警告和六条引擎启动警告。保留原日志，不把它称为零错误通过。

用户保存并关闭编辑器后，已通过 `Tools/Build/Build-Editor.ps1` 完成普通 Editor 构建：68 个构建动作，重新编译冲刺组件和角色并链接 `UnrealEditor-FPSGAME.dll`，结果 `Succeeded`。日志：[build-20260919-175907.log](../../Saved/BuildEditor/build-20260919-175907.log)。重新打开工程即可加载 ASH-12 冲刺入口。

按用户规则，不启动实机、不渲染、不追加自动测试，最终手感由用户测试。
