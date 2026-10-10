# 第三人称法杖直接复用第一人称右手抓握

> 这是对应阶段的制作记录。当前接入、替代关系和恢复依赖以[第三人称动作发布说明](../Publication/ThirdPersonActions20261010/README.md)为准；旧手工抓握表及被否定的腕臂姿态不作为当前基线。

用户否定继续手调的第三人称手型，要求直接复用当前第一人称法杖右手。本轮撤销第三人称专用姿态表对第一人称姿态的覆盖。

## 实际姿态来源

第一人称的实际手模由 `StaffWeaponComponent.cpp` 加载：
`/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7`。

`StaffGripPose.cpp` 使用 `StaffAuthoredReleaseAnatomy20261001.h` 的持杖/释放姿态、`StaffAuthoredPrimaryV28.h` 的普通攻击，以及 `StaffAuthoredChargeFlow20261001.h` 的积蓄。`StaffArmsMeshComponent::FinalizeBoneTransform` 完成局部混合，并把整条右臂搬到同帧法杖握点。这是本轮复用的运行姿态来源；不从旧 VRE 候选或手调拇指表取值。

## 接入

- 装备构建：从 `StaffGripPose::Get(...).Local[0]` 读取整手姿态，使用原生掌面映射的 Mount，把第一人称的 `HandInGrip` 和法杖 HoldPoint 一并搬到第三人称。
- 动作采样：直接读取第一人称手模已发布的组件空间姿态，经同一个 `FPSBodyStaffGrip::Transfer` 转接到角色手骨。持杖、攻击及施法使用同一路径。
- 跨骨架转换：通过两套参考掌面转换第一人称的参考姿态旋转差，包含五指和存在于两套骨架的掌骨。保留 Jason 的骨长、局部位移、缩放和辅助半关节；不做新的指尖 IK、碰撞优化或人工拇指角度调整。
- 现有全身攻击/施法层已按 `StaffHandRotation` 对腕部基准做重定位，继续使用该路径；不为抓握更换动作时序或命中点。
- 保留现有 Jason 钢甲网格及分段绑定，跟随同一套身体手骨。此次没有重写第一人称资源、第三人称装备网格或材质。
- 装备缓存键加入本实现标记，热更新后的下一次装备同步重建挂点与手部映射，避免继续使用上轮缓存。

`FPSBodyStaffGripData.h` 保留为旧候选源记录，已不再被运行代码引用。此前 `author_staff_grip_facing20261009.py`、`author_staff_thumb20261009.py` 生成的手型不再控制第三人称法杖抓握；旧接触统计与离线图不代表本轮版本。

构建回执在 `SourceAssets/ThirdPersonStaffFirstPersonGrip20261009/`。本轮按要求读取实际第一人称抓握链路并完成接入，不另行启动游戏、截图或验收；最终观感由用户测试。

本轮完成状态：游戏版构建成功；用户关闭 UE 后，编辑器基础 DLL 已成功编译、链接并落盘。此前 Live Coding 因整个工程待编译动作数超过上限而取消，不计为生效依据；交付以本轮基础构建为准。没有重新打开编辑器或启动游戏。
