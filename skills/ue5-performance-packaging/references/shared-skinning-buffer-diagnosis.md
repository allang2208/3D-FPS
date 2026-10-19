# 共享蒙皮输出缓冲的慢态归因

用于 FPSGAME 中怪群出现后，怪物与玩家装备一起变慢、相同 Morph dispatch 相差数百倍的排查。使用已有采集；新采集和运行按用户授权执行。

## 先确认能否比较

- F6 帧窗口、UE trace 和 WDDM 必须按单调时钟锚点求交集；同一个 session ID 不代表时间重叠。检查 manifest 的收尾、丢事件和权限状态，区分 `available_files_finalized` 与完整 GPU bundle。
- 清空 F6 帧样本不应停止独立 GPU trace。World 销毁后，显式采集由 GameInstance 持有并在新 World 重新连接；普通帧历史仍按 World 隔离。
- 比较同一帧、同一 shader/顶点数、同一资源身份与访问角色。按每条 GPU 队列的序号重建事件；父子 scope、并行队列、current/previous 指向同一资源时不重复求和。

## 分开两种长耗时

GPU scope 的起止跨度会包含等提交或队列空洞。与实际提交的 GPUWork 区间求交，再看 CPU 的 RHI translate、描述符分配、驱动调用及 queue wait。

本项目已有两种不同证据：一次首刷长帧中，`CreateDescriptorHeap` 的 42 次调用合计约 6.26 秒，GPU 长 scope 大部分处于未执行工作区间；另一次持续慢态中，同为 162110 顶点的 Normalize 从约 0.0082 ms 到 3.17–3.75 ms，慢 scope 位于已提交工作区间，没有同窗新建描述符堆。不能用前一次 CPU 提交问题解释后一次所有慢 dispatch。

## 显存口径与生命周期

- RHI 资源清单是逻辑分配量，不是物理驻留。放置资源需要关联父堆；共享输入、独立输出和 transient 别名分别记账。同名双缓冲不是泄漏证据。
- D3DKMT 的进程/段计数不能证明某个 UAV 被迁移。逐资源结论需要资源—父堆—物理段—调度事件关联；缺少该映射时保留未知。
- 找长期拥有者：例如 GameInstance 的 StreamableHandle 是否把互斥备用武器版本全部保留。候选字面量表不是当前装备集合；身体、默认对象和库存先占用有限准入额度，推测候选显式开启。包路径与对象路径需统一后去重。
- 不因 Nanite/VSM 池或当前场景材质体积大就删除；先确定用途、共享关系和可释放生命周期。无逐堆证据时不改放置资源的驻留优先级，不加全局 flush/GPU 等待。

2026-10-19 对照中，关闭多余武器候选后逻辑 RHI 清单约减少 392 MiB；这不等于物理显存减少同样数值，也未证明 FPS 提升或持续慢态根治。完整历史数据与限制在工程 `Docs/Performance/shared-buffer-residency-and-driver-findings-20261019.txt`。

## 采集器本身的约束

`FTraceAuxiliary::Start/Stop` 同步广播委托，AudioInsights 监听器会访问 AssetRegistry 内存资产。控制动作放游戏线程；ETW、写盘与收尾放后台，退出时不能形成游戏线程和工作线程互相等待。只停止自身拥有的 trace。

WDDM 错误 5 表示权限不足。保留可用 UE 时间线和缓冲身份并标注缺失；需要 WDDM 时由用户通过项目启动入口确认 Windows UAC。不要在游戏内循环重试、自动提权或关闭已有编辑器。

授权做对照时记录实际分辨率、二进制散列、种子、存活数、视角及后台负载。离屏窗口可能被系统缩小；命令行期望尺寸不能替代实际尺寸。死亡换视角、并发重编译或重负载离线解析会限制性能比较。
