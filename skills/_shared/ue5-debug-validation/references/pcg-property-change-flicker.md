# PCG 属性通知导致的重建

FPSGAME 丘陵曾出现玩家静止数分钟后仍整棵树、整片草消失，不到一秒恢复。最终用户确认修复成功；这不是所有类似闪烁的通用归因。

- 若用户提供 F6/GPU/log，先核对时间窗口是否重叠，再关联组件存活、pcg_start/generated/cancelled 和 render_dirty。帧时间导出不能独自证明某个 GPU pass 出错；没有 over-budget 也不能独自排除全部渲染问题。 原因：不同时间窗口或不同粒度的证据无法直接互相归因，帧总时长不包含具体 pass 的因果信息。
- 此例捕获到 75 次 PCG 取消及已生成树组件销毁。沿调用链发现 UDynamicMeshComponent::SetMesh 在 WITH_EDITOR 下广播属性通知，PCG 将丘陵拥有者的地面/水面提交当作输入变化，清理并重建各植被层。后台地形继续提交，因此原地也会反复发生。
- 修复局限于同步 SetMesh：对关联 PCG 层调用 StartIgnoringChangeOriginDuringGeneration(Component)，用 ON_SCOPE_EXIT 配对 StopIgnoringChangeOriginDuringGeneration(Component)。地面、池塘、河流三条提交路径都经过同一助手。
- 保留正常 Mesh 通知、显式地形编辑和距离调度；不要靠全局关闭 PCG 刷新、隐藏错误、缩小密度或扩大剔除距离掩盖本原因。 原因：近景、掉落物和远处实例的可见条件不同，共用一套距离策略会留下未处理的成本。
- 区分代码/构建、用户反馈和实机复测。保留足够的小型最终证据后，已结束采集的 ETL/utrace、截图、旧 DLL/PDB 可按用户整理授权归档；当前 FPSGAME.log、活动采集和生产模块不按旧文件名清理。 原因：历史采集可以归档，活动日志和生产产物仍被当前工作使用；文件名不等于退役依据。

代码：TemperateHillsStreaming.cpp 的 HillsStreaming::SetCellMesh。证据：Docs/Publication/HillsVegetation20261115/Evidence/flicker-capture-findings.json。
