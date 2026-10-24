# 第三人称双枪改用真实全身来源

2026-10-22。用户再次指出双臂扭曲，并询问为何不直接套用参考源。随后用户已将官方 Twinblast 原包加入 FPSGAME。本轮已完成原动作读取、Jason 重定向、资产保存与运行源码／配置接入，构建状态见本目录交付回执；实机观感尚未测试。

## 查实的来源区别

- 原第一人称双持：`PistolDualWield20260914` 的本地可编辑动作，依据用户指定视频重建，包含分侧手臂及武器；该视频不是可直接重定向的第三人称骨骼动画。
- 当前第三人称：`DualPistolStandards20261020/author_stances.py` 取 Jason 已重定向的 `Pistol.Idle`、`Pistol.Walk.Fwd`、`Pistol.Jog.Fwd`，再重算右臂、镜像左臂并套第一人称掌向。属于合成稿，不是真实双枪全身 donor。
- 旧 GitHub 筛选没有导入实际双枪全身动作。ALS 的代码或通用动作库不能证明本项目已获得双枪原片段。

## 选定取得的候选源

Epic Games：[Paragon: Twinblast](https://www.fab.com/listings/9fa88852-5711-42e1-94fa-2491498a64da)。2026-10-22 读取官方页面，产品免费，包含角色、动画、皮肤、特效及动画蓝图，说明可用于 Unreal Engine 项目。仅取实际动作并重定向，原始二进制不向公开仓库再分发。

首次排查时，本机 `Content`、`SourceAssets`、`D:/FPS3D/VaultCache` 中没有 Twinblast 全身模型或动作；其他 Paragon 包中的同名贴图不算源动作。用户随后将原包加入 `/Game/ParagonTwinblast`。本轮通过用户已运行的编辑器及互斥桥读取与保存，没有主动启动编辑器、游戏、截图或验收。

实际读取的骨架为 `/Game/ParagonTwinblast/Characters/Heroes/TwinBlast/Meshes/TwinBlast.TwinBlast`，237 骨；目标为当前配置的 Jason 基础身体。原动作的局部轨道、层级、绑定与脚步标记保留在 `source-poses.json`，重定向轨道在 `retargeted-poses.json`。

## 已定位的运行覆盖点

旧 `FPSPlayerBodyAnimInstance.cpp` 先由 `DualUpper` 混合三段资产，但完整源动作还会被以下层再次改写：

1. `FPSBodyPistolPose.inl::DualPistolHandTarget` 用 `IndependentPistolRotation` 替换手腕朝向，并重设肩腕轨迹。
2. `FControls::Solve` 依据新腕点做两骨 IK；换弹／装备会另换肘极。
3. 末尾 `FitStaffArm(..., false, true)` 重新构造上臂、前臂滚转和辅助骨。
4. `FitDualPistolFinalClearance` 可再次移动手腕、求解并调用 `FitStaffArm`。

因此本轮同时改变了消费者：`FPSBodyDualPistolSource.inl` 使原版完整手臂拥有常态持枪；瞄向整体旋转肩以下手臂，保留肘、腕及 twist 骨的相对姿态。上述腕目标、常规两骨 IK、最终整臂重建和净空拟合不再覆盖源持枪链。左右射击按本手 `LastShotAt` 采样对应原片段的局部旋转差量，作用于本手锁骨至腕和辅助骨，不把另一把枪一并带动。

各枪仍保留原机械／接触时钟；Twinblast 科幻枪械片段不能代替 M1911 弹匣、G18 弹鼓、DW715／RSH 弹巢的操作。交接使用 0.12 秒整臂局部姿态混合。用户随后明确要求检查换弹，查出右手甩枪的腕点跳位及普通手枪移动换弹的弹匣穿身：换弹现也沿完整 Twinblast 手臂运输较小源差量，普通弹匣的后伸路径独立适配。详见 [换弹专项记录](../DualPistolReloadReview20261022/README.md)。装备、砸击、施法、消耗品、翻越和单持保留此前路径。最终 component pose 写回 local pose 仍保留，过渡后记录最终实际腕点供外部动作恢复使用。

## 实际保存与引用

`retarget_source.py` 在独立目录创建两个 IK Rig 和一个 Retargeter。锁骨、上臂—前臂—腕、双侧 upper/lower twist 站、指链均映射；三段脊椎到 Jason 五段脊椎使用插值。等长骨链按顺序传递旋转，保持目标原生骨长；关闭 IK 目标重解算，未重建肘极或镜像另一侧。原生源包没有修改。

所有候选动画保存于 `/Game/Characters/JasonPlayer20261003/TwinblastDual20261022/Retargeted`。运行角色如下：

| 配置键后缀（前缀 `DualPistol.Source.`） | Twinblast 原片段 | 时长 |
| --- | --- | --- |
| Idle | Idle | 10.000 s |
| Walk | Walk_Fwd | 2.233 s |
| Jog | Jog_Fwd | 1.867 s |
| Sprint | Sprint_Fwd | 1.033 s |
| FireRight | DoubleShot_Fire_Rt | 0.600 s |
| FireLeft | DoubleShot_Fire_Lft | 0.600 s |

另保存了 `Primary_Fire_Med_A/B` 作为原片段制作输入，未将其整段双臂运动接到每手射击入口。现有下身方向步态保留，上身步频以原 `LeftPlant/RightPlant` 接触时间映射为 `L/R`；本轮没有制作额外方向或瞄准姿势资产。第一人称及原生握枪手指/机械骨不改。

`publish.py` 通过配置事务仅写六个角色键；旧合成稿键保留为缺少新资源时的兼容路径，正式完整配置优先选择真实源。`Config/DefaultGame.ini` 增加新动画目录的 Cook 引用。配置保存回执为 `published.json`，资产保存回执为 `retarget-receipt.json`。

## 本轮状态

- 已取得官方源，保存八段重定向动画，六段实际接入；原版肩肘腕关系成为新的持枪基线。
- 源码、配置与 Cook 引用已落盘；正式构建结果单独记录，不冒充画面结果。
- 未执行运行测试、截图、蒙皮回归或联机验收；最终自然度、各枪握持与动作交接由用户体验。

正式 Editor 构建 `build-editor-02.log` 成功，36.62 秒；Game 构建 `build-game-01.log` 成功，59.98 秒。首次 Editor 编译的局部变量遮蔽错误已改名修正，失败日志保留。交付回执为 [delivery.json](delivery.json)，记录实际六个入口、资产和源码散列；没有启动或重启 GUI。
