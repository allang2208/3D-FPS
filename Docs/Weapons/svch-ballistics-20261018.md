# SVCH 中距离瞄准弹道修复（2026-10-18）

用户反馈中距离经常无法命中怪物。本轮沿 `FireShot → ComputeShotDirection → ComputeWeaponAimDirection → FPSBallisticsComponent → RangedAttackQuery → ApplyHit` 排查。

## 原因与修改

`UpdateADSPose` 已使用 `SVCHWeaponAssets::RearSight/FrontSight` 标定机械准星，`GetNativeMuzzleTransform` 也已使用本枪实测枪口。`ComputeWeaponAimDirection` 却缺少 SVCH 分支，落到共享骨架的 `WPN_FrontSight`。共享骨骼保留供体位置，与可见准星不一致；因此目标查询和飞行弹都沿错误射线发出，误差随距离放大。

初步参考绑定复算已显示供体准星与本枪准星不一致（静止绑定估算约 6.03°，记录在 `legacy_direction.json`）。加载当前网格和实际动画后的定向运行中，旧射线与可见准星射线偏差约 **16.12°**，50 m 目标平面的偏差约 **14.45 m**。这两个数值对应静止参考绑定和实际动画两种输入，不能混用；当前运行结论以 `runtime-assertions.log` 为准。

修复只为 SVCH 机械准星增加分支：读取当前动画帧的 `WPN_root`，将本枪 `FrontSight` 转到世界空间，再由眼点指向该可见准星。继续优先使用倍率镜的相机中心与红点/全息的光学瞄点。ADS 输入开启及 ADS 混合尚大于 0.98 的过渡阶段均沿既有精确瞄准规则处理。

本轮没有修改 V9 手模、动作、枪体、瞄点、伤害、弹速、射程、散布或怪物碰撞配置。当前弹道是无重力直线分段追踪；`545 m/s` 弹速、`320 m` 有效射程并不会让 20–100 m 的静止目标因射程上限失去命中。动态目标仍需考虑正常飞行时间。

## 定向复现与回归

在现有 `BallisticPresentationAudit` 中增加显式 `-SVCHBallisticAudit` 分支，要求专用存档名，使用空地图、NullRHI 和当前 R8 网格/认可动作，无截图、无正式存档写入。

| 路径 | 范围 |
|---|---|
| 原机械准星 | 20、50、100 m，将敌方受击代理放在可见准星射线上；记录旧共享准星射线角差和横向偏差 |
| 实际发射 | 调用 `FireShot`，等待真实 `FPSBallisticsComponent` 飞行和伤害回调，比较命中位置 |
| ADS 退出过渡 | 输入松开但 ADS 系数仍为 1 时仍读取本枪准星 |
| 视模偏转 | 测试世界中临时偏转视模，确认射击追随可见准星而非强制锁定相机中心；不改动画资产 |
| 遮挡 | 眼点到枪口间的近墙、飞行路径上的远墙均应挡住目标伤害 |
| 腰射 | 保留相机轴线和已有随机散布 |

`FPSGAMEEditor Win64 Development` 构建成功（600 步，退出码 0）。定向运行 `svch-ballistics-fixed-01` 已完成，**42 项检查全部通过，进程退出码 0**：

- 20、50、100 m 的可见准星射线均穿过目标，旧供体准星射线均脱靶。
- 修复后的三种距离均实际发射、命中敌方受击代理并收到伤害；命中位置与可见准星查询点误差小于 1 mm。
- ADS 退出过渡与视模临时偏转两种情况均命中并造成伤害。
- 眼点至枪口之间的墙体触发枪口遮挡；25 m 处的墙体拦住飞行弹，两种情况都未伤害墙后的目标。
- 腰射保持相机轴和随机散布。

报告位于 `SourceAssets/SVCHBallistics20261018/runtime-assertions.log`，完整日志为同目录 `svch-ballistics-fixed-01.log`。测试使用独立 `-UserDir` 和 `SVCHBallisticAudit_*` 档案，不触碰正式存档，没有截图或渲染。敌方代理用于隔离射线与伤害链路，不作为全部怪物模型或联机模式的验收。

制作与日志：`SourceAssets/SVCHBallistics20261018/`。共享源码修改前副本保留于其 `Before/`；这些副本只用于本次差异追溯，不可整文件回退覆盖后续并行改动。
