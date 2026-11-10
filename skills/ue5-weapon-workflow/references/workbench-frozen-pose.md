# 工作台冻结姿态

适用于 FPSGAME 把实际装配武器转换为非物理展示副本的路径。2026-11-09 Viper／PKM 修复说明：不能用局部动画骨骼替代最终成品姿态。

- 从源 SkeletalMesh 获取最终 component-space 骨骼，包含动画后处理和程序修正，再转成父局部变换写入 PoseableMesh；立即刷新骨骼之后才停用 tick。仅 CopyPoseFromSkeletalComponent 可能遗漏 PKM 弹链／提把等程序修正，导致静态配件保持采样姿态而主体回到参考姿态。
- 保留源 BoundsScale，尤其 Viper 的既有防剔除包围范围；不要把该膨胀范围直接复用于精确鼠标命中。
- 展示配方与现装配图一致，包括管式霰弹枪装填导轨和 M24 枪栓外观。工具走 production tool builder，不假定存在 melee world_mesh。
- 弓的静态根组件可能有意为空，要检查实际渲染子组件；异步完成应等待相关 tool-loading handle，而非只判断根网格或任意加载队列结束。
- 展示副本不拥有库存，不启用世界拾取物理碰撞。居中、转向、缩放后的组件变换需要保持一致。

历史结构检查：69 个可强化装备定义＋25 个 Viper 单槽选项＋出厂重置共 95/95，NullRHI 加载真实资产并检查有限正包围盒、最终姿态和组件变换。不是全部跨槽组合、渲染效果、鼠标拖动或所有未来装备的证明。初次 PKM 12.55 cm 偏差在复制最终姿态后消除。

证据：`Docs/UI/enhancement-display-model-audit-20261109.md`、`Saved/EnhancementDisplayAudit20261109/report.json`。运行 `EnhancementDisplayAudit` 要有当前用户测试授权；正常展示继续异步加载，不复制审计路径的同步等待。
