# 篝火可见性与高炉同款燃料条修复（2026-10-13）

本轮针对用户“火焰很淡／看不出替换，燃料条与高炉不一致”的反馈。只改篝火专用特效与显示，不改燃料消耗、容量、存档、木工台、伤害、网络或灯光数值。

## 已确认的证据

- 检查时，正式源码、Editor DLL 和 Game EXE 均含 `/Game/Building/Campfire20261013/TorchFire/NS_CampfireTorchFire.NS_CampfireTorchFire`，两个二进制未检出旧 Realistic 完整路径。此前整体编译阻塞已不再阻止这个引用进入二进制。
- 存量建造在 `VoxelBuildWorldPrefab.cpp` 重建时通过 `LogicClass` 生成逻辑 Actor；篝火构造函数设置特效，建造存档并不保存 Flame 组件的资源路径。已经运行的旧进程／实例仍可能保持旧状态，本轮没有运行游戏验证它们，也不能由用户截图单独证明资源版本。
- 原火焰材质是 Unlit Translucent，自发光最终乘 0.1，无 EyeAdaptationInverse。透明度曲线在归一化年龄 0.15 达到峰值，随后持续衰减到 0；贴图 Alpha 同时被从 1 升到 2 的消隐指数削弱。材质结构与参数存在明确的白天可见性弱点；未把它宣称为实景唯一根因。
- 篝火 `RefreshCampfireJob` 只更新 `AnimFuelRatio`，未执行 `FuelBar->SetPercent`。`RefreshJob` 在篝火分支提前返回，跳过高炉末尾的条刷新；此外篝火将填充色固定为 Warning。共享条的初始 percent 为 0，所以燃料文字有值而填充仍空。

## 特效修复

修改同一个篝火专用 `NS_CampfireTorchFire` 和 `M_CampfireTorchFire`，无重复系统。原厂 `/Game/TorchFire`、旧 Realistic 及篝火烟材质保持原样。

- 火焰生成率 12 → 16/s；其余两层、出生半径14 cm、贴片62–76 cm、寿命1.1–1.55 s、组件位置和统一缩放不变。
- Alpha 改为 `0.95 × smoothstep(0,0.08,age) × (1-smoothstep(0.65,1,age))`，保持完整贴图火舌更长时间，再平滑消退。
- 消隐指数改为 `0.9 + 0.4 × smoothstep(0.65,1,age)`；保留纹理遮罩，避免整段寿命反复稀释主体。
- 原色彩与贴图继续使用，自发光指数收敛为每粒子1.15–1.4，末端倍率0.12；加入一次 EyeAdaptationInverse，强度1，抵消日间曝光对自发光的压暗。没有新增灯光、提高场景曝光或增加发射器。
- DepthFade仍为4 cm；固定包围盒与局部空间保持；保守稳态粒子估算38个／系统，原最多8处篝火的调度预算不变。这个数字不是性能采样。

修改先在独立资产宿主完成，检测到用户打开编辑器后，通过项目互斥桥在该编辑器中实际保存正式包。随后把保存文件复制到独立宿主重新加载并验证，未从外部覆盖活动编辑器的已加载包。

## 燃料条修复

新增纯显示助手 `Source/FPSGAME/UI/ColdSteelSmeltingPresentation.h`，把原高炉的燃料渐变、冶炼颜色与百分比写入集中使用。`ColdSteelSmeltingWidget.cpp` 与 `ColdSteelCampfireWidget.cpp` 调用同一函数，继续共用原有通栏轨道、填充几何、火星动效和10Hz数据刷新。

篝火占比仍是 `剩余燃料秒 / FuelConfig.Capacity`，补充容量为零时的保护。55秒／600秒的预期填充为9.1667%，不会伪造为满条。分钟／秒仍使用高炉的 `ReadableSeconds`；篝火上限明确取其真实燃料配置，高炉仍按自身容量升级计算。没有改数值、扣除、添柴或料理逻辑。

最终未改 `ColdSteelSmeltingWidget.h` 的反射类布局；原本高炉颜色计算原样移到共享助手，不另造一套近似样式。

## 验证边界与回退

- 资产从保存包重新加载，Niagara valid，三层 sprite renderer、无粒子灯、局部空间与固定bounds均确认；材质中恰有一个曝光补偿节点接至Emissive，Alpha和消隐表达式读回一致。
- Game完整构建已执行；Editor／Live Coding最终状态与日志以 `SourceAssets/Campfire20261013/TorchFire/VisibilityV2/delivery.json` 为准。Live Coding成功也不等于基础Editor DLL已常规重建。
- 两张Library参考图按官方消费端流程尝试物化，但Windows Python缺少 `os.setxattr`，最终路径未落地。没有绕过该错误或查看临时残留文件；未声称看到截图像素。图像ID、失败状态记录于交付回执。
- 未启动游戏、PIE或新的GUI编辑器；无真实存档写入、实景截图、GPU渲染验收或性能采样。视觉效果仍需用户实机确认。
- 本轮 `Before/` 保留修复前源码、专用包与作者脚本；`baseline.json` 包含原厂资源散列。回退只恢复本轮两份特效包和UI显示改动，保留后来并行修改，不整库回退。

重建顺序：原 `author_torch_campfire.py` → `adapt_materials.py` → 本目录 `apply_visibility_fix.py`。最后一步按唯一节点描述更新，避免重复增加材质节点。正式引用与资产身份沿用原路径。
