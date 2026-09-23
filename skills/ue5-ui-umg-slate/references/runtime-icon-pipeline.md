# 运行时图标准备与定向刷新

适用于动态武器/模块化物品图标首次打开卡顿及图标就绪引发库存全量刷新。保留当前目录图回退、配方缓存、玩法装备和存档合同。

小图标按捕获尺寸申请 mip，不以全套源贴图 IsFullyStreamedIn 作为无期限门槛；加载／准备任务有尝试上限和回退，离线目录制作可使用独立的完整贴图等待。后续改动沿用 [性能开发约束](../../ue5-performance-packaging/references/fpsgame-performance-development.md) 的驻留与重试预算，避免补回永久强制驻留或无限队列。

- 异步 GPU 回读只解决回读等待，不能消除前面的同步资源加载、展示角色初始化、配件装配和 CPU 蒙皮包围盒计算。分别记录这些阶段。
- 从当前配方所选零件/材质的同一目录逻辑构造软引用清单，异步加载；handle 保留到装配和捕获准备结束。取消、切换配方和反初始化时释放。不要预载全部武器家族，也不要为探测可选资源而同步加载。
- 展示初始化只载当前网格、idle 与可见配件；通过明确参数跳过不需要的战斗动作、音效和 FX，玩家正常装备路径保持原行为。UObject 与组件创建仍在游戏线程。
- 将准备流程拆为跨 tick 阶段。耗时顶点遍历用分块合作预算并保存游标；分块间观察时间不是严格的单帧上限。需要精确包围盒时保留全部可见顶点，并区分图标/掉落物坐标系后复用结果。
- 区分资源等待年龄与 CPU 工作耗时；记录等待对象、阶段、请求年龄、尝试年龄和失败原因。不可将等待超时或缺资源永久记为成功；离线作者导出所需同步加载不扩大到运行时。
- 图标完成通知携带配方键，订阅者只更新关联可见物品的刷子或 Paint。模型内容变化继续走原有数据刷新，不把所有事件一律降为绘制失效。
- 高频诊断文本只在内容变化时设置；一份事件快照单次汇总多个统计栏目，复用已有行控件。不要通过重建整个控件树“刷新”未改变的数据。
- `Too many texture coordinate sets ... GPUSkin` 先核实真实使用者与材质 usage。静态附件从骨骼母材质克隆后可能误带 skeletal/morph/cloth/自动用途；只有确定不用于骨骼时才清除不适用用途，保留原 UV、接缝、湿润与法线图，不先重排 UV 或隐藏错误。

FPSGAME 源码：`ColdSteelWeaponIcons`、`ColdSteelIconResources.cpp`、`ColdSteelWeaponIconReadback.cpp`、`ModularSwordVisual::GatherVisualResources`。采样解释见 [性能面板归因](../../ue5-performance-packaging/references/performance-panel-attribution.md)。
