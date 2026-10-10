# 第三人称持杖施法动作（2026-10-09）

> 这是对应阶段的制作记录。当前接入、替代关系和恢复依赖以[第三人称动作发布说明](../Publication/ThirdPersonActions20261010/README.md)为准；旧手工抓握表及被否定的腕臂姿态不作为当前基线。

当前抓握与原生腕臂作者共用规则见 掌向与穿模返工历史稿（已归档，见[归档清单](../Publication/ThirdPersonActions20261010/archive-manifest.json)），本日两段施法已随该修复重新制作和保存。

后续反馈：用户指出手腕扭曲；原姿态不作为认可基线。已按 腕部返工历史稿（同一归档清单） 同步修改作者骨链解算、持杖基准及最终运行时腕臂层。

## 范围与来源

本轮处理第三人称持杖施法的完整右臂。复用本地 Kay Lousberg 的 KayKit Character Animations 1.1（CC0）中的 `Ranged_Magic_Raise`、`Ranged_Magic_Shoot`，先通过已有 KayKit→Jason retargeter 转换，再按 Jason 原生骨长、当前 VRE 整掌握柄姿势适配。它们是施法供体的适配版，不是未经修改即可使用的法杖动作。

许可：`SourceAssets/ThirdPersonSwordFree20261005/KayKit/KayKit_Character_Animations_1.1/License.txt`。
原来源：https://kaylousberg.itch.io/kaykit-character-animations 。本轮不新增外部素材下载。

## 处理内容

- `ReadActions` 原先使用 `IsOccupyingLeftHand()`，排除了持杖施法的真实阶段进度；`CaptureMotion` 又把阶段名覆盖成统一的 `StaffCast`。现在直接读取共享施法执行器的手势进度，用 `Contacts.Channel` 区分持杖，保留 Gather / Ready / Release / Recover。
- 新动画层播放肩、肘、腕的原生局部姿态，停止在这一层叠加第一人称相机空间的腕部目标。供体提供动作节奏、肩部参与和肘部方向；离线根据原生骨长及真实持杖掌向调整肘部转向，辅助骨保持所属骨段的 rest-local 关系。
- 举杖截取供体起势，移除原供体自带的停留、回落段；释放截取前送和跟随。举杖末帧与释放首帧共用完整姿态，释放肘平面从实际举杖末帧连续过渡。
- 四种握柄继续使用 `FPSBodyStaffGripData` 的整掌、四根掌骨、拇指和四指姿势。新动作记录作者参考掌向，运行时适配当前握柄；法杖仍刚性附着于最终手骨。
- Ready 从实际入场姿态接到举杖末帧；Recover 从最后实际播放姿态接回实时持杖。取消蓄力不会先补播到举满位置。恢复读取原阶段进度，没有新增施法计时器。
- 上半身姿态跟随实时骨盆高度和瞄准俯仰；腿部仍由行走、蹲伏与落地层驱动。左手维持既有手部目标，副武器射击、装备和换弹独立。
- 发射动作的 Contact 标记对齐执行器现有 `0.18 / 0.28` 的前挥阶段比例；后续停留与恢复仍由原执行器控制。原法术扣蓝、占用、瞄准、弹道和接触回调未修改。

## 交付

保存并登记到 `player_body.json`：

- `Staff.FullBody.CastGather` → `/Game/Characters/JasonPlayer20261003/StaffCast20261009/Animations/J_KayKit_Staff_FullBody_CastGather`
- `Staff.FullBody.CastRelease` → `/Game/Characters/JasonPlayer20261003/StaffCast20261009/Animations/J_KayKit_Staff_FullBody_CastRelease`

烹饪目录只新增上述 Animations 目录。Source/Donors 为制作材料，不是运行时选择。

制作脚本位于 `Tools/PlayerBody/{prepare,author,save}_staff_cast20261009.py`；作者数据、保存回执、后台命令日志及修改前备份位于 `SourceAssets/ThirdPersonStaffCast20261009/`。运行时主体为 `FPSBodyStaffCastPose.inl`。

依用户规则，仅后台制作、保存与必要构建；不运行游戏、PIE、截图、渲染或验收。动作观感、极端瞄准角及装备组合待用户测试，不把资产保存或编译成功当作视觉验收。

后台结果：两段资产最终保存命令退出 0；`FPSGAMEEditor` 与 `FPSGAME` Development Win64 均构建成功（退出 0）。保存时的默认 30 fps 压缩采样不整帧问题已改为作者 60 fps 采样；最终保存正常完成。未进行游戏测试。
