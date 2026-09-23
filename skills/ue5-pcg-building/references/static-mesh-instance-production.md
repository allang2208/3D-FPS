# 静态构件的 Nanite 与实例化制作

用于把已生成的重复石构件、栏杆和装饰合并为局部 ISM。以下接口经验来自 UE 5.8.2；其他版本先对照本机接口。它不是运行时交互 Actor 的批量替换规则。

## 保持生成语义

- 限定明确生成标签、普通静态构件和授权关卡。按局部空间、网格、材质、碰撞、导航及组件配置分组，保留每个构件的世界变换。组尺寸按场景选择，避免整片地图合成一个包围盒。
- 有附属 Actor、额外组件、顶点涂色、物理模拟、重叠/交互事件或独立逻辑的对象保留。实例化后的 Actor 身份会改变，依赖独立对象身份的玩法不能直接合并。
- ActorPosition 或 WPO 材质可能在合并后改变语义；先判明材质兼容性。Nanite、显式切线、回退网格和碰撞分别配置，开启 Nanite 不等于碰撞或回退几何自动满足需求。
- 先创建完整实例组，再移除对应原对象并保存地图。记录源对象/变换与组结果，重跑不重复转换已有实例组；生成器调用同一分组入口，避免重建恢复旧策略。

## UE 5.8 接口限制

- `FBodyInstance::CopyBodyInstancePropertiesFrom` 只接受未初始化的 BodySetup 默认实例；关卡组件的 BodyInstance 已有关联所有者，直接复制会断言。复制可编辑物理配置，保留新实例的 owner、句柄与场景状态；不要整体赋值已注册 BodyInstance。
- 静态网格通过 `SetStaticMesh` 设置。反射批量复制不能直接覆写 `StaticMesh` 指针而跳过通知，否则触发 `KnownStaticMesh` ensure；自定义复制应排除该字段并调用 setter。
- Nanite 设置保存与派生数据构建是不同步骤。如果后续转换要求 `HasValidNaniteData()`，先完成网格构建；UE 5.8 `Build(true, &OutErrors)` 提供错误容器时采用同步构建。不要把暂时无派生数据误记为“没有可分组对象”。
- PythonScript commandlet 中 `StaticMeshEditorSubsystem` 可能为空。可用 `get_editor_property('nanite_settings')` / `set_editor_property(...)` 发属性通知，必要时调用上述 C++ 构建入口；地图用 `EditorLoadingAndSavingUtils` 加载/保存，不依赖面板子系统。
- 不需要捕获或渲染的配置制作可使用 `-NullRHI`。它不证明 shader 渲染通过；实际渲染或 shader 验证需求再选择真实 RHI。快速切换材质 usage 曾触发着色器任务队列断言，应区分引擎队列失败与 Python 接口错误。
- 接入回执在每次成功保存后写入。进程非零退出时先读保存位置和错误原因；已保存部分不能无条件重复执行，也不能把最终出现“saved”视为全部无错误。

FPSGAME 示例入口：`Source/FPSGAME/Development/PlazaInstanceTools.*`、`SourceAssets/MainScenePerformance20260923/`。这些制作脚本与构建不自动授权 PIE 或视觉/性能验收。
