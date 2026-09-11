# FPSGAME 怪物反馈回归（2026-09-11）

宿主为 `D:/FPS3D/FPSGAME`。详细证据与失败保存在 `Docs/MonsterFeedback20260911.md`、`SourceAssets/MonsterFeedback20260911`；新的通过数字读取 acceptance-summary.json，不能沿用旧 30 项结果。

- 手脑 SurfaceV07 的旧胶囊接地通过，仍可能有大量真实表面穿地。死亡轴位于首个物理骨上方时，验证物理 root 是否存在，并比较刚体世界变换与实际渲染骨骼。新增不碰撞 root 后还要核对宽手掌是否超出轴向胶囊。本例使用 base/neck/cranium 三个实际主体顶点凸包；死亡时缩小的备用攻击附件不扩大主体凸包。保留骨骼缩放逆换算。
- 通过当前 RefToLocal 蒙皮矩阵读取物理混合后的表面；GetCPUSkinnedVertices 会刷新动画，可能覆盖物理姿态。使用真实地面组件检测采样点，并保留完整尸体画面。至少检查不同死亡方向；仅刚体 AABB、关节位置或 IsSimulatingPhysics 不足以验收。
- 毒滴对象查询会命中 OverlapAllDynamic 的雾体/触发盒。先收集接触，再选真正阻挡的表面或玩家主胶囊。本项目玩家胶囊忽略 Visibility，不能直接改成单一 Visibility trace 而遗漏玩家。
- 村庄攻击必须验证真实命中/玩家生命变化。只有动画、发射次数或判定窗口通过仍可能完全无伤害。场地回归包含发射点位于重叠盒内、穿过重叠盒命中玩家、后方墙体阻挡。
- 控制效果和 HUD 分离：状态栏读取真实 Poison/Fear 组件、监听层数变化，倒计时按 0.1 秒刷新。显示通用 Buff 记录不等于已实现该 Buff 的玩法。
