# 大旋风 V4：连续蓄势与入场衔接

用户已确认镜头帧同步修复成功，本版按后续授权优化0.5秒蓄势的僵硬与跳帧感；完成后用户反馈整体没问题。最后追加的移动/跳跃限制属于运行逻辑，尚待成功编译接入。

## 动画源

`whirlwind_motion.py` 使用共享节点速度的五次 Hermite 轨迹，节点加速度相接。回拉0–0.14秒、蓄住0.14–0.34秒、展开0.34–0.50秒；减少原220ms近乎静止的区间，在蓄住阶段保留小幅连续运动。0.50秒的横持节点具有非零运动速度，与后续横扫属于同一条曲线。仅真正改变运动方向的轴减速到零。

武器位置、握柄转动和刃面相对转动共享时钟；双手由现有 Manny 连续双臂求解器针对同一握柄轨迹求解。保留既有手指抓握、骨段长度、前臂辅助骨和肩肘支撑。镜头继续由运行时完成 -720度，不额外烘焙转身。

`author_whirlwind.py` 输出普通柄 `Whirlwind_Manny_Editable.blend`、`Export/A_RuneSword_WhirlwindV4.fbx`。`author_long_grip.py` 保留普通柄全轨道和时序，对加长柄左臂沿用现有18mm握距适配，输出 `LongGripExport` 下的FBX与可编辑关键帧JSON。

总业务时长1.82秒（蓄势0.5、旋转0.8、收势0.52），480Hz资产采用874个采样间隔。源脚本创建独立V4资产；V3旧动画现已归档，V3前景材质继续使用。

## 运行时入场

新增剑专用 `URuneSwordMeshComponent`，继承现有 `UFPSCastingMeshComponent`，保留施法覆盖层能力。施放时在切换动画前捕获实际显示的完整骨骼姿态，第零帧继续显示该姿态；前0.1秒按五次曲线混合到当前大旋风采样。该0.1秒包含在0.5秒蓄势内。

混合在骨骼父空间进行，保持骨段长度。WPN_root与双臂共用权重；混合后按各手相对剑柄的握持变换设置腕目标，使用两骨IK修正肩肘，必要时由锁骨小幅补偿可达范围。手指及辅助骨保留混合后的局部关系。剑骨及其子骨作为握持目标保留，不随手臂IK被重复搬动。

混合在 FinalizeBoneTransform 的骨骼缓冲区提交前完成，剑身挂点随最终姿态一起更新。0.1秒到期以及取消/结束都释放入场快照。沿用已获用户确认的 PostPhysics 调度，不再引入镜头缓存晚一帧问题。

## 接入

- 普通柄：`/Game/Weapons/AzureRunesword20260913/A_RuneSword_WhirlwindV4`
- 加长柄：`/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations/A_RuneSword_WhirlwindV4`
- 原生：`Weapons/RuneSwordMeshComponent.h/.cpp`、`RuneSwordComponent.cpp`、`RuneSwordWhirlwind.cpp`
- 导入：通过现有串行接入桥执行 `import_revision.py`；普通柄和加长柄分别保存回执，已有目标不会自动覆盖。

新原生组件通过常规Editor构建接入，需重新创建运行实例。本轮默认不启动游戏、截图、渲染或追加检查测试；素材保存与构建结果不代表视觉效果已验收，交由用户测试。

普通柄/加长柄导入均已保存，回执为 `import_receipt.json` 和 `long_grip_receipt.json`。完整Editor构建成功：`Saved/BuildEditor/build-20260920-183009.log`；原编辑器正常退出后已重新启动工程，未启动PIE或运行测试。
