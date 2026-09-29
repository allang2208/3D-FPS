# 其他三种移动姿态专项调整 V11

日期：2026-09-29。用户要求“其他的移动姿态也同样检查并调整”。

**交付状态：三段 V11 动画及现有毒液僵尸蓝图已导入并保存。** UE 抽样求值中容器根缩放为 1；SOURCE 与 COMPRESSED 的最大骨骼位置差分别约为 B 0.0617 mm、C 0.0634 mm、Run 0.0841 mm。本轮完成离线动画及导入片段检查，未进行游戏试玩。

本轮逐段检查并重制 Walk_B、Walk_C、Run_A。Walk_A 继续使用 V10；完整 Attack_A、近战和生成时固定动作/步速的原生逻辑保持原接入。这次是动画资产更新，不需要新增原生构建。

## 发现与处理

- **Walk_B**：旧接触判定把左脚每次支撑拆成两段。改用允许脚底滚动的慢走接触范围，支撑窗合并为每周期两段；放缓着地混合，减少侧倾，并保留肩到手腕的滞后。
- **Walk_C**：除同类脚部切换外，前臂存在明显角速度尖峰。附加肘部弯曲改为稳定的骨骼局部弯曲方向，避免在接近伸直时每帧叉积方向反转；保留较明显的左右不对称姿态。
- **Run_A**：独立设置头部保留比例和周期平滑；去掉循环边界“停在中间姿势、再快速离开”的短窗口处理。接触判定增加踝部高度条件，避免后摆中的腾空脚再次被判为落地；保留腾空。
- 三段都从干净原生重定向片段重新制作，使用贯穿周期的接缝修正和环形取样，保留现有 Meshy 骨架、蒙皮与材质。

## 离线结果

按最终导出的 FBX 每秒 60 帧取样，并渲染实际导出的蒙皮模型。下表为组件空间每帧四元数夹角计算的角速度峰值，单位为 °/s；峰值下降是局部急转减少的证据，不代表游戏效果自动验收合格。

| 姿态 | 头部峰值：V10 → V11 | 左前臂峰值：V10 → V11 | 匹配步速 cm/s |
|---|---:|---:|---:|
| Walk_B | 161.5 → 99.5 | 239.8 → 148.4 | 55.877 |
| Walk_C | 122.0 → 93.3 | 324.4 → 198.3 | 55.540 |
| Run_A | 798.2 → 263.4 | 594.9 → 403.9 | 199.085 |

采样中的足部蒙皮最低点均未低于制作地面。该结论限于本次足部权重筛选范围和采样时间，不是游戏地形碰撞测试。左右差异、跑步腾空和循环边界仍应在用户试玩中确认。

## 预览

以下为原速离线灰模检查，材质展示不是游戏中的最终绿色材质。三列分别为 Walk_B、Walk_C、Run_A。

![三种移动 V11](D:/FPS3D/FPSGAME/SourceAssets/SpitterZombieMeshy20260927/LocomotionV11/OtherMovement_V11.gif)

各段前后对照均为左 V10、右 V11：

- [Walk_B 对照](D:/FPS3D/FPSGAME/SourceAssets/SpitterZombieMeshy20260927/LocomotionV11/Walk_B_before_after.gif)
- [Walk_C 对照](D:/FPS3D/FPSGAME/SourceAssets/SpitterZombieMeshy20260927/LocomotionV11/Walk_C_before_after.gif)
- [Run_A 对照](D:/FPS3D/FPSGAME/SourceAssets/SpitterZombieMeshy20260927/LocomotionV11/Run_A_before_after.gif)

## 源与引擎交付

- `author_locomotion.py`、`authoring.json`、`SpitterZombie_LocomotionV11.blend`、`Final/`：可重建制作源和三个 FBX。
- `InspectV10/measurements.json`、`InspectV11/measurements.json`：逐帧检查记录及渲染帧。
- `install_locomotion.py`：通过现有 UE 编辑器桥导入、绑定、保存，并对三个片段做 SOURCE/COMPRESSED 抽样比较。只写指定动画与现有毒液僵尸 BP。
- `installation.json`：实际保存记录；文件中包含 UE 动画求值结果。没有该记录不能把制作文件等同于已导入资产。

本轮没有启动、关闭或重启编辑器，没有启动 PIE 或执行游戏回归。离线动画和导入片段检查属于本次用户要求，实际游戏效果留待用户确认。
