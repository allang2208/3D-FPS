# 法杖主手的快速进战

2026-10-01：F 和快捷栏继续调用 `quickCombat`。当前主手为法杖时，空副手使用左手直拳；副手为手枪时固定使用双持系统的左手近战片段。右手保持法杖握持。

- 左拳使用 V7 原生裸手骨架的完整左臂局部姿态表。反馈修订将 0.115–0.20 秒的前伸段按 ×1.5 提速，接触改为 0.171667 秒，总长 0.551667 秒；后续时间整体提前 0.028333 秒，回收段时长不变。0.291667 秒后逐步交还当前待机／移动姿态。可编辑源及生成入口在 `SourceAssets/StaffQuickCombat20261001/`；游戏使用 C++ 姿态表，不需要额外导入动画 uasset。
- 副手枪复用当前 `QuickCombatClipKind(1,true)` 和 `Pose()`，保留 fitted／long 及自动手枪空仓分支。M1911 法杖副手分支改用 `StaffQuickCombatFix20261001/M1911/l` 的六条完整腕臂修正版，其他组合仍沿原共享 Profile 路径。源动作总长按实际片段读取，保持 0.80 秒、0.18 秒接触。法杖组合不轮换出手侧，不采样失活的右手枪。
- `UFPSQuickCombatComponent` 管理一次扣体力、一次接触、钝器伤害／击退、确认音、使用／击杀修炼和动作结束解锁；不增加独立冷却或眩晕。命中先采样接触时刻再读取 `middle_01_l`。
- 空手拳不继承法杖的武器精通／符文快照；副手枪快照来自实际左手枪。技能基础数值、体力和装备倍率仍沿用现有快速进战公式。
- 统一优先权中断取消法杖普攻／照明手势，并沿现有施法退款路径处理被中断法术。动作期间法杖普攻、施法和副手射击／换弹等待；切换装备、菜单、攀爬或死亡解除本次动作。

本轮只制作、接入和必要构建；未运行游戏、测试、截图或渲染。动作手感与视觉效果由用户测试。

## 初版后台构建与落盘

Editor 与 Game 两个 Development 目标均构建成功（exit 0）。基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 与 `Binaries/Win64/FPSGAME.exe` 已由常规构建落盘。日志分别为 `Saved/BuildEditor/staff-quick-combat-editor-20261001-154422.log`、`Saved/BuildEditor/staff-quick-combat-game-20261001-154422.log`。没有启动／重启 UE 或运行游戏。

可编辑动作已保存为 `SourceAssets/StaffQuickCombat20261001/Staff_FreeLeft_QuickPunch_20261001.blend`。实际运行复用原有法杖 V7 网格与副手枪资产；左拳直接消费生成的 C++ 原生骨姿态表，没有新增待导入的 UE 动画资产。

## 用户反馈后的腕臂诊断与修订

用户指定问题枪为 M1911。只读检查旧 V5 作者数据与 UE 已保存的原始／压缩轨道：前伸与接触早段没有执行 `natural_hand`／`support_twist`，这些解算只覆盖转枪恢复窗口。旧源 0.125 秒附近腕轴夹角超过 100°；固定肩腕后仅改变肘极点仍无法降至自然范围。共享 Profile 的局部差值和全 rig 瞄准旋转不是首次出现此缺陷的层。

修订将持枪组掌向、完整肩肘链和原生辅助骨一起调整，保留枪手接触、正常／空仓机械状态及完整转枪。新作者源位于 `SourceAssets/StaffQuickCombatFix20261001/M1911LeftArmV6/`，运行时只在 `bOffhandOnly` 的 M1911 左主攻六个档位选择新片段。空拳同时重做闭合四指与拇指外扣，并将蓄势腕点移到镜头后方，增强短促前伸和接触镜头反馈。

诊断数据位于 `Saved/StaffQuickCombatFix20261001/Diagnosis/`。本次未追加游戏、视觉或回归测试；最终握拳姿态、腕臂形状与手感由用户测试。

## 修订版落盘结果

- 左拳表版本为 `StaffAuthoredQuickPunch20261001::Revision=2026100102`，运行缓存按该版本重建。可编辑 Blend、完整姿态 JSON 和生成脚本均已实际保存。握拳制作改用现有认可的 `LeftHandPowerFist20260923/fist_profile_v2.json`，并适配本法杖 V7 的指腹与指甲方向。
- M1911 六条修订 AnimSequence 已通过无界面 Python commandlet 导入、压缩并保存。`SourceAssets/StaffQuickCombatFix20261001/M1911LeftArmV6/import.json` 记录六个已保存资产；导入日志为 `Saved/StaffQuickCombatFix20261001/import-m1911-v6-20261001-1608.log`，commandlet exit 0。FBX 是仅骨架动画，未导入新网格、材质或贴图。Interchange 对 FBX 骨架节点报告零时绑定姿势警告，导入结果为六条已保存动画，没有游戏视觉结论。
- 常规 `FPSGAMEEditor` 构建结果为 up to date／Succeeded，`FPSGAME` 构建 Result Succeeded、exit 0。日志分别为 `Saved/StaffQuickCombatFix20261001/build-FPSGAMEEditor-20261001-160733.log`、`Saved/StaffQuickCombatFix20261001/build-FPSGAME-20261001-160733.log`。基础 Editor 模块与 Game 可执行文件沿常规构建落盘；没有启动交互编辑器或游戏。

旧左拳输出已归档，当前 FixV2 拳形参数与后续动作制作输入继续保留，见 `SourceAssets/FPSArmsPublication20261002/archive-manifest.json`。
