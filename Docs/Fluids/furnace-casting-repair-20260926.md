# 高炉金属液体修复（2026-09-26）

用户要求检查并完善前一轮未成功的高炉金流。当前实现替换为连续几何液柱、锭模液面、稀疏飞溅及冷却后的配方金属锭。它是解析流动表面与材质动画，不是实时流体求解器。

## 本轮定位

旧入口 `Tools/Fluids/author_furnace_tap_metal.py` 和旧运行逻辑存在以下问题：

- 金流 update 使用上一帧 `Particles.Position` 再加累计年龄位移与重力项，不是以固定出生点求解析轨迹。横向项还错误地把 `Position.y` 与高度常量 63.5 相减。轨迹随帧率发散，不能停留在出铁口到锭模之间。
- `M_TapMetalFlow` 未接 `ParticleColor` 与 `Opacity`；旧颜色/消失包络根本没有进入材质。形状函数在卡片边缘仍输出非零发光，容易显示方片。
- 液池与余晖共用 `FaceCamera` billboard，不能形成水平锭模液面；流的落点也没有对齐中央模腔。原锭长轴 24 cm 大于中央模腔。
- 出铁更新位于烟雾分配的 `continue` 之后；六个烟雾名额占满或烟资产未就绪时，出铁状态被跳过。
- `TapMeshLoad` 完成后立刻释放句柄，金属锭网格和四种材质没有稳定强引用，后续 `ResolveObject` 可能失败。
- 归还的 TapFX 仍被旧炉持有，旧炉继续写参数可关闭其他炉的新事件。锭池满时默认占用 0 号、槽从未释放，隐藏锭也未清空引用，返回范围和后续炉次无法正确复用。
- 最新旧日志没有本效果的编译告警；之前的缺 SubUV 纹理/usage flag 修补已存在，不能再当成本轮根因。

## 新表现

- 原创低面数网格 `SM_FurnaceCastingSurface` 共 2,112 三角面：连续圆截面液柱＋中央锭模内的水平液面。主体写深度，不是叠加小卡片。
- 网格坐标仍为炉体局部厘米；`Body` 恒等挂接，四个放置朝向自动随炉旋转。
- 炉内起点 `(17.5,0,63.5)` → 出口 `(24.7,0,63.5)` → 中央模腔 `(45,0,26.2)`；水平出口后按重力弯落。液柱末端随填充高度下降，接入实际液面。
- 材质时间取世界游戏时间减每组件 `CustomPrimitiveData[0]`。UV 沿流向滚动，表面起伏、亮金/橙红变化；细节种子在 `[1]`。无需每帧 C++ 更新顶点或创建动态材质实例。
- 约 0.48 秒抵达模腔，填充液面；3.2 秒停止出料，尾流约 3.68 秒流尽；随后由亮金冷却为暗红，5.4 秒切换配方金属锭。实际切换由既有 5 Hz 更新执行。
- 固态锭长轴调整为 14.8 cm，按真实 bounds/pivot 将底面放在模腔底部。铁/铜/银/金材质继续来自原配方；取出、拆炉、坠落或离开 85 m 时释放展示，返回后可恢复已完成锭。
- Niagara `NS_CastingDroplets` 只做实际落点的飞溅小滴，透明边界归零并接粒子颜色和 alpha；其预算不足不再抹掉金属液柱主体。

## 接入与成本

运行实现从共享子系统中拆到 `Source/FPSGAME/WorldGeneration/FurnaceCasting.cpp`。原烟雾更新仍使用原有 5 Hz 调度，但出铁判断移到烟组件分配之前。没有增加世界 tick、碰撞、光源或同步加载，也没有修改冶炼、燃料、库存或存档数值。

连续浇铸最多 4 个组件（共 8,448 个源三角面）；飞溅 12 粒/秒、每粒最长约 0.277 秒，每次最多 4 个系统。锭展示池按需增长，最多对应登记表的 32 座炉，不抢占其他炉的可见锭。以上为制作预算，不是实测性能。

异步批量预载句柄保留到子系统退出，持有液柱/锭网格与材质。新液柱网格有显式 soft UPROPERTY 引用。归还对象时隐藏/停用、解除父级、清空借用引用；炉被删除时先归还展示再移除登记。

## 可重建源与资产

- `Tools/Fluids/build_furnace_casting_mesh.py`：Blender 后台几何生成；输出 `.blend`、FBX 与 `geometry.json`。
- `Tools/Fluids/author_furnace_casting.py`：材质、FBX 导入与 Niagara 作者入口。
- 原 `author_furnace_tap_metal.py` 的命令行入口转到新作者；旧辅助函数只供模板作者复用。旧源码快照在 `SourceAssets/FurnaceCasting20260926/BeforeRepair`，未删除旧资产。
- 已保存目录 `/Game/Fluids/FurnaceCasting20260926/`：`M_CastingStream`、`M_CastingPool`、`M_CastingDroplet`、`SM_FurnaceCastingSurface`、`NS_CastingDroplets`。
- 本轮保存回执 `SourceAssets/FurnaceCasting20260926/receipt-20260926-171807.json`；同目录 `assets.json` 汇总当前制作参数。

## 检查与构建范围

针对用户明确要求的“检查”，本轮读取源码、旧日志，并检查本效果保存资产的尺寸、材质输出、参数与绑定。没有打开编辑器、启动游戏、PIE、截图或进行性能测试。

首轮原生构建：`Saved/BuildEditor/build-20260926-171520.log`，`Result: Succeeded`。最终构建回执：`Saved/BuildEditor/build-20260926-171951.log`，`Result: Succeeded`，目标已是最新。共享工作目录的正常构建已纳入最后修改：`FurnaceCasting.cpp.obj` 时间 17:18:46、`FluidPresentationSubsystem.cpp.obj` 17:18:47、基础 `UnrealEditor-FPSGAME.dll` 17:19:09，均晚于最终源码/头文件的 17:18:11。第二次构建并未重复执行编译动作，不把它写成独立的全量重编译。

资产实际执行：`Saved/Logs/furnace-casting-author2-20260926.log`，commandlet 返回 0，五个 `FURNACE_CASTING_SAVED`，Niagara `valid=1`，`FURNACE_CASTING_COMPLETE`。采用 D3D12/SM6 与 `AllowCommandletRendering` 编译材质，无本次三种材质的编译失败；同进程已有 GrassDeform 材质报错属于其他效果，没有修改该资产。首次作者运行因 Substrate 发光 pin 名写成 `EmissiveColor` 失败，随后按当前 API 修正为 `Emissive Color`；成功记录以上述第二次为准。

实机观感及性能未测试，由用户确认。后台构建/保存与静态资产检查不等同于实机验收。

保存资产独立读回：`Tools/Fluids/inspect_furnace_casting_assets.py`，回执 `SourceAssets/FurnaceCasting20260926/asset-inspection.json`，commandlet 返回 0。实际导入包尺寸约 34.90 × 7.60 × 38.95 cm、中心 `(34.95,0,45.47)`，轴向和单位与生产源一致；两材质槽、三种 Substrate 输出、Opacity/Mask、Niagara Sprite 用途、CPD 索引及四个 User 参数均完成本题范围内检查。未运行游戏。

> 2026-09-27 发布整理：BeforeRepair 作者快照已移至 trash/forging-publication-20260927/SourceAssets/FurnaceCasting20260926/BeforeRepair。当前连续液柱作者与仍被引用的旧辅助函数保留。
