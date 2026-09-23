# 场景几何成本与 LOD 收敛（2026-09-23）

> 本文件记录 2026-09-22/23 主场景广场制作与性能回归中**可复用**的判据与 API 事实。
> 那一次的过程记录在 `Docs/Performance/plaza-geometry-regression-20260922.md`，
> 任务级结果以该正本为准；本文件只保留能用在下一类任务上的部分。

仅在用户要求检查／测试时执行下文的采样与读回校验。日常制作优先遵守 [性能开发约束](fpsgame-performance-development.md)，不要把一个广场的参数直接套到多层地牢。

## 1. 性能面板的 `all_rank_total` 是 LOD0 口径，看不出 LOD 效果

`all_rank_total` 按 `(triangles + .1*vertices + 2500*material slots) * instances` 计算，
用的是**资产 LOD0** 面数。给网格加 LOD 链之后这个数字**一点都不会变**。

主场景一次实测：加 LOD 前 `all_rank_total` 20,691,645，加 LOD 后仍是 20,691,645，
而 `gpu0` p50 从 30.51 ms 降到 11.28 ms、`draw` p50 从 34.96 ms 降到 6.60 ms、`window_fps` 从 27.03 升到 47.97。

**结论：判定 LOD 工作是否有效，看 `gpu0`/`draw` 的 p50、`window_fps`、`over_budget_fraction`，
不要看 rank 指标。** 只看 rank 会误判为"毫无改进"。

## 2. 组件数量不能单独确定瓶颈

同一次实测里，**组件数完全没变**（693 actors / 715 meshes），`draw` p50 却降了 5.3 倍。
这说明该次收益不能由组件数量的减少解释；几何相关工作是候选原因，不能据此断言所有场景的渲染线程都主要受三角面驱动。

推论：在拿到"组件数不变而 draw 明显下降"这类证据之前，不要按"每图元固定开销"的假设去做
整边网格合并——那会牺牲 LOD 粒度（合并后包围球变大、屏幕尺寸阈值不再触发）
而未必换来收益。按证据区分提交、材质、几何与可见性成本。新制作的重复刚体可复用已有实例化方案；整块合并要保留独立交互、碰撞和剔除边界，不把实例化与破坏性合并视为同一动作。

## 3. UE 5.8 生成 LOD 链的正确调用

下例是明确重建本次拥有的 LOD 链时的写法。增量接入不要先删除已有作者 LOD；保留原始资产与碰撞策略，再决定哪些档位需要制作。

`unreal.EditorStaticMeshLibrary` **没有** `set_lod_count`（按名猜会 `AttributeError`，
而且该库整体已废弃）。正确路径：

```python
smes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
smes.remove_lods(mesh)                      # 先塌到 LOD0，保证可重复重建
settings = []
for pct, screen in ((1.0, 1.0), (0.25, 0.35), (0.08, 0.1)):
    s = unreal.StaticMeshReductionSettings()
    s.set_editor_property('percent_triangles', pct)
    s.set_editor_property('screen_size', screen)
    settings.append(s)
options = unreal.StaticMeshReductionOptions()
options.set_editor_property('auto_compute_lod_screen_size', False)   # 用我们给的阈值
options.set_editor_property('reduction_settings', settings)
smes.set_lods(mesh, options)
mesh.post_edit_change()
unreal.EditorAssetLibrary.save_loaded_asset(mesh)
```

坑：`set_lods` 的第二个参数是**一个结构体**，不是数组。
直接传 `list` 会报 `StaticMeshReductionOptions: Struct has 2 initialization parameters,
but the given sequence had 3 elements`。

生成后必须**读回逐档面数**核对（`mesh.get_num_triangles(i)`）；减面没生效要报失败，
不能假定调用成功。

## 4. 大面积平铺件需要适合其包围体的 LOD 策略

一块 16.7 m × 7.7 m 的铺装板，其包围球半径约 9.85 m。相机站在广场中间时，
在该测试机位的屏幕尺寸很大，既定阈值可能持续选择 LOD0；不能把这一机位推广为所有距离和视角永远不触发。

可按实际网格选择分块、合理屏幕阈值或 Nanite。只有已经确定近景轮廓、缝隙与表面质量满足需求，且资产存在目标 LOD 时，才在相应组件强制该档位。例如强制 LOD1：

```python
comp.set_editor_property('forced_lod_model', 2)   # 0=自动；正数=LOD 索引+1；1 实际强制 LOD0
```

读回校验也用 `forced_lod_model`（写 `forced_lod` 会静默失败）。
小构件（柱、矮柱）不需要强制——它们屏幕尺寸小，阈值会自动把它们降到 LOD1/LOD2。

## 5. 地板阴影取决于实际遮挡作用

广场单层地板若下方确实没有受光对象，且不承担其他遮挡，可按该资产用途考虑关闭投影。不能由 LOD0 面数断言 VSM 每帧都会处理它的全部三角形；还受可见性、缓存和 Nanite 路径影响。

地牢地板可能是下一层的天花板，台阶、栏杆底座与缝隙也有实际遮挡作用。不要按“地板”命名批量关闭 cast_shadow，更不能把此案例扩展为全场无阴影。

## 6. 密集装饰资产不要铺满大范围——先看面数密度

`SM_MarbleFloorTiles` 是 1800 × 800 × 5 的一块板、**120,140 个三角面**（≈834 面/m²）。
查它的生成脚本可知：造法是 `append_box` 一块板 + 切 24 条 100 cm 网格的 1 cm 宽凹槽 +
`compute_polygroups`/`bevel`。**这 12 万面是布尔切槽之后没有收敛的网格碎片，不是有意做的细节。**

把这样一块"为小面积做的"资产铺满 100 × 100 m = 78 块，就是 937 万面，
占全场景几何量的 51%。

判据：**先算面数密度（面/m²）× 目标覆盖面积**，再决定是否平铺。
面数密度明显高于观察距离所需时，改用低面数底板 + 材质，或先补 LOD 链；
布尔产生的碎片网格通常可以大幅减面而不丢外观。

## 7. 交付口径

- 加 LOD / 改阴影 / 强制 LOD 都要**读回校验**（逐档面数、`forced_lod_model`、`cast_shadow`），
  并把回执写盘；不要凭调用返回值推断生效。
- 资产级改动（LOD、Nanite）会改变共享资产，需说明影响到的其它使用者。
- 未跑 PIE / 未截图时如实说明；帧率结论只来自用户导出，不由几何量推算。
