# 草地 v14：修复膨胀包围盒压小弯折角

**最新状态：2026-09-27 用户再次反馈未成功，已转待办并暂停。v14 实例参数尚未全部保存，不是完成版。** 后续以 [暂停与源码发布记录](grass-paused-publication-20260927.md) 为准；下文保留本次定位与部分制作过程，不能把单项代码问题扩大为已解决视觉问题。

用户反馈 v13 在测试中几乎没有变化。本轮按此现象定位和修复；未主动开启游戏、录制或运行回归。

## 原因

v11–v13 的材质用 `InstanceLocalBounds` 估算草片根部到最远顶点的距离，再用 `2*asin(MaxOffset/(2*BladeBound))` 给整片刚性旋转限角。但 UE 5.8 会先把最大 WPO 位移加到此渲染包围盒中：

- `Engine/Source/Runtime/Engine/Private/InstanceData/InstanceDataManager.cpp`：`ComputeAbsMaxDisplacement` 加入材质最大 WPO；`ApplyDataChanges` 对实例 Bounds.Min/Max 施加 PadExtent。
- `Engine/Source/Runtime/Engine/Private/PrimitiveSceneProxy.cpp`：`BuildUniformShaderParameters` 将上述实例边界写入 `Builder.InstanceLocalBounds`。
- `Engine/Source/Runtime/Engine/Private/Materials/HLSLMaterialTranslator.cpp`：`InstanceLocalBounds` 节点读取该 PrimitiveData 边界。

因此“为防止裁剪增大 WPO 余量”反过来增大了弯折限幅所用的杠杆长度，压小实际转角。以模型 03_08 中一个近中央根部、测试场约 150 cm 高和 1.425 倍横向缩放估算，静态杠杆约 147 cm，加入 320 cm 边界余量后约 962 cm，旧限角约 18°。这能解释为何设定 74° 目标后依然大致直立；这是源数据与公式估算，非实际 GPU 顶点测量。

此前 v12 的 RT 压力、接触时序断言没有覆盖最终顶点转角，故其通过不能否定此缺陷。

## 修复

- `MF_GrassDeform` 改为 `mf-v14`，用制作阶段存入材质实例的 `GrassRestBoundsMin/Max`，来源为静态网格原始包围盒，不读取渲染器扩展边界。
- 按实际材质归并关联网格的边界。共享材质使用边界并集，保证整片统一限角，保留防拉裂、长度和宽度的约束。
- 覆盖 PN 草库使用 MA_Grass 的网格材质，以及丘陵复制品使用 M_TemperateMeadow 的网格材质；高草测试场复用后者。
- 实例缩放明确连接 ObjectScale 的 `Scale XYZ` 输出。原渲染边界 320 cm 与物理位移上限 300 cm 保留，但不再形成反馈。
- 新增 `Tools/GrassDeform/rest_bounds.py`，主材质作者和丘陵重新制作脚本共用，避免重建后丢失尺寸参数。运行时没有新增 CPU 遍历、纹理或 RT 绘制。
- 保留 v13 的 0.6 秒保持＋1.8 秒恢复、74° 目标、80 cm 半径和身体保压，本轮不叠加力度／半径调参。

## 诊断依据与落盘

- 当前编辑器启动于 12:50，在最新 DLL 和 v13 材质保存之后。实际草地材质读取到 `mf-v13`、位移上限 300，设置保持时间 0.6；不是单凭文件时间猜测版本。
- 只读输入快照：`Saved/GrassResponseInputs20260927/125709/inputs.json`，包括两个测试草网格、材质参数、模型三角形与 PivotPainter 源数据导出。
- 第一次制作提交被正在运行的 PIE 阻止，尚未修改资产；等待当前游戏停止后在现有编辑器内通过 MCP 互斥批次制作。
- 停止 PIE 后的制作回执：`SourceAssets/GrassDeform20260927/authoring-20260927-130431.json`，12 项基础资产已保存，两个主材质及四个通道材质的编译错误数组均为空；完整修复前备份为 `SourceAssets/GrassDeform20260927/BeforeV14-20260927-130431`。
- 此次实例参数制作遇到 UE 5.8 向量 setter 返回值问题：引擎已写入参数但固定返回 false。已改为读取刚写入的参数确认再保存。继续制作时 DayNight_Lighting 再次进入 PIE，批次在修改前停止；实例参数还未全部落盘，不能把当前中间状态作为完成版。
- 用户已要求暂停，不再等待 PIE 后自动续跑。仅在用户重新要求开发时，才考虑运行 `setup_assets_m1.py` 完成剩余实例参数；本轮不宣称实机视觉通过。
