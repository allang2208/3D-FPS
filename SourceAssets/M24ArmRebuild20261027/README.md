# M24 双臂基础动作重建，2026-10-27

本版对应“左肘关节异常、拉栓右手扭曲，要求检查动画源并重新优化整套基础动作”。

## 原因与修改

- 旧 UE 动作加握持配置与旧 Blender 作者源一致，主要错误存在于源姿态。旧版只修改冲刺和拉栓窗口，基础持枪及其衍生动作仍带有供体骨架的上臂旋转。
- 按原生 V9 骨架重建左右肩—肘—腕关系。上臂旋转与肘弯平面对齐，上臂辅助骨跟随同一形变坐标；前臂旋转由原生 twist 辅助骨分担。左侧臂根向外调整，腕部接触点保持原位置。
- 逐动作计算连续肘部路径，保留边界姿态，避免每帧独立选择肘朝向造成跳变。
- 重新拟合枪栓握持方向与手指姿势。右手经过离开握把、绕开枪体、接触枪栓、随枪栓运动、回握几个阶段。过渡两端统一在最终求解的同一个前臂坐标系中插值。
- 去掉旧右手末节手指的供体轴向旋转，使用原生指关节轴弯曲。旧近战基础动画存在右手指关节位移；保存姿态层时保留恢复原生指骨偏移所需的差量。
- 覆盖 14 条作者动作：idle、aim、equip、fire、cycle、reload、reload_empty、inspect、quick_melee、sprint_enter、sprint_loop、sprint_exit，以及 10 发弹匣的 reload_mag10、reload_empty_mag10。

## 接入

运行时继续复用原有基础 AnimSequence，通过已保存的完整双臂姿态层叠加本版修正。本版作者配置：

- `/Game/Weapons/M24/ArmRebuild20261027/DA_M24_SupportGrip`
- `/Game/Weapons/M24/ArmRebuild20261027/DA_M24_Mag10`

同一份新版数据同时保存到现有入口 `/Game/Weapons/M24/MotionPolish20261027/DA_M24_SupportGrip` 和 `DA_M24_Mag10`；保存前的两个资产原始字节保存在 `Backups/`。`Source/FPSGAME/Weapons/M24WeaponAssets.h` 沿用现有入口，本版无需新增 C++ 接口即可被当前模块读取。枪体机械轨道、枪栓事件时钟、弹匣事件时钟和基础动画时长保持现有接入。普通换弹和空仓换弹仍走各自分支，10 发扩容弹匣保留独立换弹姿态。

可继续编辑的作者源：`M24_ArmRebuild_Editable.blend`。`Exports/` 内为本版 14 条 FBX。导入使用临时作者动画烘焙姿态层，不额外保存一整套重复运行时动画。原生蒙皮、网格、骨架参考姿态及 corrective morph 资产未改动。

## 本次请求范围内的复查记录

- `source_before.json`、`source_after.json`：全部 14 条动作的 30 Hz 源姿态和骨架诊断。
- `ReviewFrames/` 与三个 `*_source_sheet.jpg`：拉栓、空仓换弹、进入冲刺的源动画关键帧。
- `CameraFrames/`：沿用项目持枪相机标定的源姿态视图。它们是 Blender 源动画视图，不是 UE 游戏截图；只近似应用原生肘腕 corrective 曲线，不代表运行时全部姿态叠层。
- `saved_after_comparison.json`：最终配置读取对照已补齐。通过现有 UE 编辑器的批次桥读取当前使用的两个配置，14 条动作共 193 个姿态样本与新版作者源对应，最大双臂位置差异约 0.1014 毫米，采样旋转差异在本次 float 计算精度下为 0。沿用现有实例，不强制重载包，不覆盖编辑器中的未保存资产。
- `saved_payload_comparison.json`：最后一次实际交给 UE 保存的姿态数据，与作者源进行 193 个姿态样本的对照，含两个弹匣分支；最大双臂位置误差约 0.1014 毫米。这个数字是数据一致性差异，不是手指表面接触精度或游戏视觉验收。
- `install_receipt.json`：本版两个姿态层及两个现有入口，共四个资产的实际保存结果，`complete=true`。
- `read_after_receipt.json`、`read_after_resume_runner.log`：此前等待 600 秒的批次锁阻塞已解除；本次通过正在运行的 UE 实例完成配置读取，两个弹匣分支均包含在对照中。
- `build_receipt.json`、`build_runner.log`：后台原生编译结果。本次全项目构建遇到弓箭模块缺失 `BowHeldMagicVisual.h` 及 `UpdateBowMagic` 未定义，未修改这些无关文件。最终改用上述资产入口替换，不依赖这次未成功的 DLL 构建。

未启动交互式 UE 编辑器或游戏，未进行游戏内验收。实际镜头、衣袖、动作切换和运行时叠层效果仍由用户试玩确认。
