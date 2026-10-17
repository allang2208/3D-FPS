# 守寝者 V18：重定向链路与支撑脚修正

> **最新状态：2026-10-17 用户再次判定不合格，停止继续制作，转入待办。** 以下为历史排查和数值结果，不能证明视觉通过，也不能把 V18 当作认可模板。见 [收尾与恢复边界](../Publication/NightWarden20261017/README.md)。

2026-10-17。用户明确要求排查重定向、肩背与巨臂和双腿联动、脚底打滑。保留 V17 的 `Jog_Biped_Fwd` 源动作，针对数据链路修正；V17 已被用户否定，不作为成功模板。

## 排查范围与结论

| 层级 | 本轮证据 | 结论 |
| --- | --- | --- |
| Rampage 源动作 | 源肩胯相对转动范围约 24.51°，双膝有完整屈伸 | 源动作并非静止躯干或缺少腿部动作 |
| UE 原生重定向 | 肩胯转动保留约 22.48°，双膝变化接近原动作；Root 本身没有动态位移或旋转 | 未发现主骨链丢失或动态 Root 被错误抵消 |
| 重定向 IK 配置 | `IKRetargetRunIKRigController` 的 `chains` 为空；实际为 FK 骨链迁移 | 建立了 IK Rig 资产，但没有完成支撑脚约束 |
| V17 后处理 | 七根肩背/头颈骨逐根重新定姿，加上巨臂独立延时；肩胯转动只剩约 12.33° | 后处理削弱了整身联动 |
| 脚底与速度 | 仅全身上下平移接地，支撑速度拟合还排除了反向和过快样本；离线模拟最长支撑段漂移约 28.76 / 20.05 cm | 仅同步一个平均移速无法抵消支撑期滑动 |
| 活动 UE 资产 | 实际为 V17、46 骨、原 AnimInstance、Actor 与 Mesh 缩放均为 1，RateScale=1 | 不是旧动画引用或缩放分母不一致 |
| 平台重采样与压缩 | 制作模型为 60 Hz，新建动画的平台采样率仍默认 30 Hz；偶数帧匹配、奇数帧偏离。V17 最大骨位偏差约 1.68 cm，V18 初次回读造成约 1.9 cm 脚底下陷 | 仅设置控制器帧率不够，必须同步平台目标采样率；只换压缩器仍不能消除重采样误差 |

证据目录为 `SourceAssets/NightWarden20261015/V18CoupledLocomotion/Records/`，包含 `diagnosis_before.json`、`ue_snapshot.json`、`compression_before.json` 和 `validation_default_compression_failed.json`。

## 本轮修正

保留原生肩背、锁骨和两臂的同步相位与旋转，撤销 V17 逐骨替换平均姿态和巨臂独立延时。头颈只作一次胸部空间内的固定对齐，保留周期变化。骨盆横向幅度按目标与源髋宽比例 0.8276 适配，保留移重；上下起伏按重步支撑重新约束。

双腿保持原骨长和原动作膝面，用两段骨骼解算实际脚底位置。每脚支撑周期占比 0.56，左右交替并留有双脚支撑；摆动弧线取自源动作，实际足底最高约 18 cm。以原蒙皮足底的中心及最低点迭代拟合，不把踝关节当作地面接触点，不靠整个人物每帧上下跳动修正脚底。

周期仍为 1.4 秒、60 FPS、85 键。完整周期步幅约 134.60 cm，动画基准及 AI 速度均为 96.1405 cm/s。左右接触曲线 `NW_Plant_L/R` 随动画保存，运行时直接读取相同时间，保持步频、位移与接触相位一致。

运行时 `FNightWardenFootPlantNode` 使用现有地面查询预算、两个脚底接触点和双骨骼 IK，在走路与起停混合时保持世界空间落脚点和朝向；抬脚时释放，攻击、死亡、物理和离地时停用，超过骨长或扭转范围时释放当前接触。左脚支撑跨循环端点，不能因整条动画时间回绕而释放。运行时不重新加载资产，也不遍历角色网格顶点。

本动画将 `PlatformTargetFrameRate.Default` 同步为 60 Hz，并使用独立的高精度骨骼压缩设置、禁用帧剥离；不修改其他动作或全局压缩配置。保留关键帧的编码器使用引擎默认的无量化平移和 Float96NoW 旋转。

## 当前状态

原生接触层已完成 Editor 构建，V18 动画、左右接触曲线、独立压缩设置和原蓝图均已保存；在独立后台 UE 进程重新加载后完成了压缩数据回读。`build_receipt.json` 的退出码为 0，`ue_delivery.json` 的 `complete=true`，`validation_installed.json` 的 `passed=true`。

压缩后的专项结果：

| 项目 | 结果 |
| --- | --- |
| 肩胯相对转动范围 | 约 22.45°，恢复至原生重定向范围 |
| 左 / 右脚最长支撑段前后漂移 | 0.0730 / 0.1621 cm；平地直线离线重放口径 |
| 全周期足底最低高度 | 左 0.2918 / 右 0.2933 cm，没有穿过基准地面 |
| 保存姿态与制作姿态最大骨位差 | 0.00287 cm |
| 原腿骨长度最大偏差 | 0.000048 cm |
| 循环端点位置差 | 0 cm |
| 源模型 / 平台采样率 | 均为 60 Hz |

有限骨骼数据、原生躯干扭转保留、支撑漂移、足底高度、原骨长、循环连续性、保存姿态匹配七项专项检查通过。数据和源码保存记录不能替代真实游戏的视觉与行为验收。

本轮进行用户要求的静态配置、逐帧骨骼、原蒙皮足底和压缩数据排查。没有启动游戏或执行真实转弯、坡地、起停与战斗试玩；自然度和运行时接触效果仍需用户体验。

## 制作与接入入口

- 可编辑源：`SourceAssets/NightWarden20261015/V18CoupledLocomotion/Authoring/NightWarden_CoupledStride_V18.blend`。
- 骨骼键及接触曲线：同目录 `Motion/coupled_keys.json`。
- 最终动画：`/Game/Monsters/NightWarden/V07WaistStride/CoupledLocomotionV18/Animations/A_NightWarden_CoupledStride_V18`。
- 原蓝图：`/Game/Monsters/NightWarden/BP_NightWarden`；F6 稳定入口 `NightWardenRig`。
- 源脚本：同级 `Scripts/author_coupled_stride_v18.py`、`install_coupled_stride_v18.py`、`read_retarget_state_v18.py`、`read_installed_stride_v18.py`、`validate_coupled_stride_v18.py`。
- 原生源码：`Source/FPSGAME/Monsters/NightWardenFootPlantNode.*` 和 `NightWardenAnimInstance.cpp`。

裸身与左手修复、原始网格权重、V08 待机和 V12 百目挥击均沿用既有资产。V17 的制作输入与旧动画保留用于追溯。
