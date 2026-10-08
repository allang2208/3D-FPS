# 缚群 V11：修正凸包布料连续碰撞造成的持续卡顿

> 历史阶段记录。2026-10-08 用户否定整体衣物并暂停；V18、V19 均未获认可。当前状态、最新参数和已归档证据的取回位置以[暂停与发布记录](bound-congregate-paused-publication-20261008.md)为准。

用户于 2026-10-08 要求排查怪物出现后严重卡顿。本次只修正已定位的布料求解退化，不改 V10 蒙皮、衣物表面、材质、触手发力、攻击时序、冷却或死亡表现。

## 原因与证据

V9 将贴身衣物的碰撞由胶囊扩展为表面凸包，V10 沿用了这套设置，同时保留 `UChaosClothConfig::bUseCCD=true`。实际资产包含四块衣物、8561 个代理顶点、6087 个动态粒子和 106 个凸包（两大片各 50 个，两袖各 3 个）。

当前 UE Chaos 使用 legacy evolution。`PerParticlePBDCCDCollisionConstraint.h` 对动态粒子遍历该衣物碰撞体，调用 `FindClosestIntersection`；`Convex.h` 的这条路径遍历凸包平面并建立、排序交点数组。原来用于简单胶囊的 CCD 配置在增加大量凸包后变成了高开销组合。

用户已有游戏日志中，00:18:09.008 的第 818 帧到 00:18:26.572 的第 851 帧相差约 17.56 秒；怪物首次加载完后仍连续出现约半秒一帧的间隔。截取保存在 `SourceAssets/BoundCongregateMeshy20261006/ClothPerfV11/user-session-excerpt.log`。

## 后台隔离测量

使用当前 FullWhipV10 资产和引擎真实 `FClothingSimulationInstance`，临时 EditorPreview 世界，有物理场景但不启动 BeginPlay、不推进游戏世界，不开编辑器窗口。手动推进 24 次，步长 1/60 秒，前 6 次预热，统计后 18 次。各组采用同样的小幅位移，四块衣物、材质和几何相同。

| 临时配置 | 布料求解平均 / ms | 最大 / ms |
|---|---:|---:|
| 原资产 | 429.606 | 466.132 |
| 仅关闭 CCD | 19.506 | 22.935 |
| 仅关闭自碰撞球 | 425.662 | 492.125 |
| 临时移除身体碰撞，用于归因 | 8.615 | 10.274 |

有效测量每组均有四块衣物和 6087 个动态粒子，求解器报告 6 次迭代、1 个子步。配置准备约 0.01 ms；初始化约 12–24 ms，远低于持续 CCD 求解开销。数据在 `SourceAssets/BoundCongregateMeshy20261006/ClothPerfV11/before-cloth.csv` 和 `profile-owner.log`。

早期没有成功建立布料实例的隔离运行是无效测量，不使用其零耗时结果。正式探针使用带所属 Actor 的组件和物理场景，Python 入口拒绝缺失布料实例的结果。

这些是布料 CPU 隔离耗时，不是游戏完整帧时间，也不是多怪同屏、挥鞭极限姿态或视觉验收。关闭 CCD 后仍约有 20 ms 的布料求解成本，不能据此承诺整场景 60 FPS。

## 修正与落盘

- `BoundCongregateAuthoring.cpp`：新建衣物配置使用离散碰撞，避免重建时重新引入凸包 CCD。
- `save_cloth_perf_v11.py`：只将当前蓝图所引用 FullWhipV10 网格中四块衣物的 CCD 改为 false，并直接保存已有网格资产。保留身体碰撞凸包、自碰撞、背挡约束、距离权重和其他求解参数。
- 资产备份、前后散列和保存状态记录在 `SourceAssets/BoundCongregateMeshy20261006/ClothPerfV11/delivery.json`；原始资产备份在其 `before/` 子目录。
- `BoundCongregateClothProbe.cpp` 和 `profile_cloth_cost.py` 是显式调用的 commandlet 诊断入口，常规游戏不运行，非 Editor 构建不包含探针代码。

未启动游戏、PIE 或画面验收。实际游戏流畅度和快速挥鞭时的衣物贴合由用户确认。
