# 第一人称冲刺镜头幅度减半（2026-10-13）

用户要求：覆盖所有武器，普通冲刺、战术冲刺及冲刺攻击的屏幕抖动幅度减少 50%。

## 修改

共享常量 `Weapons/SprintCameraMotion.h::AmplitudeScale = 0.5`，应用于镜头的位移和旋转输出：

- `AFPSGAMECharacter::UpdateCamera`：所有装备共用的横向/上下步频起伏、俯仰、侧倾，以及横向移动倾斜。走路保持原幅度，随原有 `SprintCameraFactor` 平滑过渡到 0.5；持续冲刺时为此前的一半。
- `UWeaponActionCameraComponent::Apply`：步枪与近战战术冲刺的前后/横向/上下位移、俯仰/偏航/侧倾及落脚脉冲，最终幅度乘 0.5。
- `URuneSwordComponent::GetCameraMotion`：冲刺下劈和 `bDashAttack` 的起势、下劈、制动振动、确认命中反馈、收势统一乘 0.5，包含从 `SprintOverhead` 高举姿势进入的冲刺攻击。普通第三段连击复用的过顶下砍不归为冲刺攻击。

战术冲刺的 `SprintStrength` 配置及 `SprintCameraWeight()` 保持原语义。它们还控制普通步频层与战术冲刺层的交叉混合，直接改成 0.5 会重新引入更多普通起伏，不能保证输出减半。

## 武器覆盖（源码排查）

当前枪械目录共 16 项：M4A1、AKM、QBZ-191、M1911、Pit Viper 2011、G18、Dan-Wesson 715、RSH-12、ASH-12、M16A2、A762、SVD、PKM、201 轻机枪、HK416、M4 Super90。均进入角色共用镜头；单/双持手枪使用共用步频层，各步枪家族和握把/弹鼓变体使用同一战术冲刺镜头输出。

当前近战目录 5 项：`ue_rune_sword`、`ue_frost_crystal_sword`、`ue_highland_claymore`、`ue_tang_dao`、`ue_xuanchi_zhenyue`，共用角色步频、剑战术冲刺与剑动作镜头分支。

另外排查了弓、法杖、魔法书/副手组合、空手、伐木斧与矿镐：它们的冲刺镜头使用同一个角色步频入口；各自的攻击/拉弓/施法镜头不是额外冲刺波形。手枪/双持、步枪和剑的手臂动画不会独立驱动屏幕相机。

本次只调整冲刺相关镜头幅度。步频、动作时长、攻击时序、冲刺速度/距离、FOV 目标、持握动画及接触点保持原值。普通走路、换弹、射击后坐、非冲刺攻击、翻越与落地反馈没有额外缩放。

## 构建边界

源码已落盘，正式 `FPSGAMEEditor / Win64 Development` 后台构建成功，15 个构建动作、15.95 秒；日志 `Saved/BuildEditor/build-20261013-101736.log`，模块 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已落盘。没有启动编辑器或游戏，没有截图、自动测试或逐枪实测；由用户体验确认。
