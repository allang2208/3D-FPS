# 长杖 V14：手腕与右臂向画面右侧调整

2026-09-27。用户确认 V13 的方向正确，要求手腕、手臂向右的幅度更大。

将相机空间中的法杖握点向 `+Y` 平移 **4 cm**。现有完整右臂随同一握点整体移动，右肩、肘、腕一起右移，保留 V13 的掌向、腕部局部旋转、手指包握及手杖接触关系。左臂沿用 V13。

待机握点由 `(44,19,-21)` 调整为 `(44,23,-21)` cm。装备、行走、奔跑、举杖、前挥释放与收回采用同一偏移；杖尖、施法焦点及近战轨迹继续由当前握点计算，施法时序不变。

## 保存与接入

- `StaffCastMotion::PresentationOffset()` 是运行时偏移入口；`StaffWeaponComponent::CarryPoseInCamera()` 和施法关键姿态共用它。
- 运行时继续读取完整 V13 局部姿态，在现有整臂握点对齐层应用右移；不重新拟合手指，不引入额外手腕扭角。
- `author_right_carry.py`、`full-pose.json`、`save_editable.py` 与 `Staff_BowBasedGrip_V14.blend` 保存了对应作者源。
- 复用已有手模和法杖资产，无需 UE 资产导入。

## 构建

常规 `FPSGAMEEditor Win64 Development` 构建成功：24 个步骤，14.42 秒，基础 `UnrealEditor-FPSGAME.dll` 已更新。日志：`Saved/BuildEditor/build-20260927-185532.log`。

没有启动 UE 或游戏，没有进行测试、截图或视觉验收；右移幅度由用户查看确认。
