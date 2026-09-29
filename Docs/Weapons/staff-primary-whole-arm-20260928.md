# 长杖普攻 V28：整臂后撤出屏，再前送下砸

用户反馈 V27「方向对了，但感觉只围绕手腕变动，没有带动手臂」，明确允许手和武器后撤超出屏幕。V27 只保留为方向参考，不视为动作细节已认可。

## 本次调整

- 起手由肩与上臂带动，肘部抬起并屈臂，手掌和法杖一起撤到右上方画面外；最大后撤时手掌位于相机后方。
- 下砸先由肩带动上臂向前送，随后肘部展开、前臂压下；继续向下随势后，再屈肘收回。五个完整关键姿态改为后撤、肩后蓄势、前送下砸、完整随势、屈肘收回。
- 作者阶段直接给定肩位置、上臂方向和前臂方向，使用原生骨长做正向运动学。四种握柄的腕部相对前臂角度及手指局部抓握沿用各自 V13 待机值，没有单独的大幅翻腕关键帧。
- 关键帧之间加入肩部、上臂略先行，肘部略滞后的局部混合。手和杖的位置来自同一套混合后的骨段，而非独立插值握点后再将整条手臂绕手腕转过去。
- 进入、退出时只平滑补偿当前携杖的展示偏移；中段由实际骨骼链完全驱动。命中震动仍整体施加，保持手与握柄接触。

V27 的 0.5 秒基础攻速、非线性加速／制动、屏幕冲量、钝击音、35／45 ms 命中顿帧与阻挡收势继续使用。实际攻速继续读取装备数值。未调整伤害、法术、存档或改造数值。

## 接入入口

- `SourceAssets/ApprenticeStaff20260927/PrimaryWholeArmV28/author_motion.py` → 四握柄完整局部姿态和握点参考。
- `StaffAuthoredPrimaryV28.h` → 当前普攻姿态表，替换 V27 运行引用；V13 的待机、走跑和施法姿态继续使用。
- `StaffGripPose::BlendLocal` → 完整骨段混合与肩肘先后；`ContactFromArm` 沿真实父骨链得到握点。
- `UStaffArmsMeshComponent::AuthoredContactInCamera` 与 `UStaffWeaponComponent::SamplePrimaryPose` → 显示、扫掠、阻挡恢复共用实际骨段轨迹。
- `PrimaryWholeArmV28/Staff_PrimarySmash_V28.blend` → 已保存四种握柄的可编辑动作，120 fps、基础 0.5 秒；脚本 `save_editable.py` 与运行时使用相同混合和正向运动学。

运行时仍使用 C++ 姿态表、既有 V7 网格和音频，不需要新 UE 动画包导入。完整骨骼采样数据和 Blender 源保留本机，遵守既有来源和再分发边界。

## 构建与未测试范围

源码、生成姿态头与 Blender 动作源已落盘。后台 `FPSGAMEEditor Win64 Development` 常规构建成功，基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已更新。日志为 `Saved/BuildEditor/staff-whole-arm-v28-20260928-105154.log`，作者目录 `build-receipt.json` 保存构建回执。

本轮未启动 UE、游戏、测试、检查或预览渲染。上文描述已制作的驱动方式和动作设计，实际视觉与手感由用户测试确认。
