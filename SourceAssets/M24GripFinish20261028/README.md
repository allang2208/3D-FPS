# M24 握持、拉栓衔接与屏幕反馈（2026-10-28）

本轮按用户要求继续检查：保持手臂与枪械模型的整体位置，修复动作内部的问题，并加入适量屏幕抖动。

## 修改范围

- 沿用当前 V9 网格、原生骨长、蒙皮、修形与枪械模型；没有修改模型几何、缩放、材质、视模组件偏移、腰射或 ADS 标定。
- 用原始 DJMaesen 动作的实际皮肤接触区域辅助拟合当前手模；手指使用当前手模的原生弯曲轴，保留骨长，不移动指节来追接触点。
- 修正共用右手握把姿态，带入 14 个作者角色（包括 5／10 发换弹分支）的持握和返回阶段。左臂、枪械各机械骨骼以及弹匣轨道保留接入前数据。
- 拉栓采用先松开手指、移向枪栓、操作、松手退回、最后合拢回握的分段安排。食指在松手阶段保留自然弯曲，避免伸直后扫入枪栓。
- 对上一版逐帧拟合产生的手腕跳变，在枪栓坐标中平滑修正量，保留枪栓自身的机械行程。
- 排查发现旧右臂求解在可达极限附近突然平移肩部，并使锁骨根部跟随上臂旋转。新版拉栓固定锁骨根部在原待机的武器相对位置，以原生锁骨长度连续转动；腕部绕圆形栓柄调整握栓角度。此修改属于右臂骨骼动作，不是整体手臂模型或枪体的搬移。

## 屏幕反馈

使用现有 `WeaponReloadCamera` / `UWeaponActionCameraComponent` 公共通道，新增四个手动枪栓接触：抬柄、后拉、前推、闭锁。各接触为 0.16–0.20 秒的短促角度反馈，原始单次角度不超过 0.60 度，平移为零；最终仍经过玩家镜头强度、公共幅度限制及退出衰减。

射击拉栓读取实际射击源时钟；空仓与仅补闭锁读取换弹源时钟和恢复起点。普通换弹不添加枪栓接触。M24 在完全 ADS 下保留 15% 的动作镜头反馈，不修改 ControlRotation、瞄准挂点或射线方向。

源码：

- `Source/FPSGAME/FPSGAMECharacterReloadCamera.cpp`
- `Source/FPSGAME/Weapons/WeaponReloadCamera.h`
- `Source/FPSGAME/Weapons/M24WeaponAssets.h`
- `Source/FPSGAME/FPSGAMECharacter.cpp` 中的 M24 动作镜头 ADS 权重

## 已保存交付

- `M24_GripFinish_Editable.blend`、`Exports/`、`final_poses.json`。
- 当前配置：`/Game/Weapons/M24/MotionPolish20261027/DA_M24_SupportGrip` 与 `DA_M24_Mag10`。
- 新版配置副本：`/Game/Weapons/M24/GripFinish20261028/`。
- 旧配置备份：`Backups/`。保存记录：`install_receipt.json`。
- `M24_GripFinish_Source.gif` 是源动画预览，未叠加游戏内镜头反馈。

## 本轮检查与边界

用户授权范围内进行了源动作接触、连续性、固定锚点及导入读取检查。`anchor_record.json` 中枪械骨骼与左臂位移变化为零；拉栓右锁骨根部相对共用握持锚点的偏差为零。右肩旧错误轨道的修正差异另行记录，不把它标成未修改。

`contact_record.json` 是有限帧、每三个右臂皮肤顶点取一个的三角表面内外诊断。检查帧的明显穿插已消除，仍记录少量约 1–2.5 毫米的局部重叠；不是完整零穿模验收。`motion_record.json` 记录手腕与肘部的逐帧最大位移，供后续动作修订定位。

常规 Editor 构建已成功，记录为 `build_runner.log`；该次构建判定当前依赖与产物已是最新。资产导入采用后台 commandlet 并保存，没有主动打开交互编辑器、启动游戏或 PIE。游戏内视场、运行时姿态层、镜头反馈与最终手感仍由用户测试。

保存后重新读取了两套实际配置及对应基础动画。`saved_layer_readback.json` 覆盖 14 个角色的选定帧，右臂骨点与最终作者姿态的最大差异约 0.123 毫米，枪械骨点差异为零；这说明保存的姿态层与本轮制作结果一致，不代表游戏视觉验收。

## 来源

Based on "sniper animated" (https://sketchfab.com/3d-models/sniper-animated-b48999a250b2433da59f705c371a49b2) by DJMaesen (https://sketchfab.com/bumstrum), CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/).

原始许可：`../M24CustomScope20261026/Donor/GLTF/license.txt`。本轮修改为原生手模适配、接触与分段轨迹修正，未引入新的外部动画资源。
