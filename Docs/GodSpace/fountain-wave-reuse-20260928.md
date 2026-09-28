# 主神空间：复用喷泉波浪与云团细节

**当前状态（2026-09-28 后续用户调整）：下方云海已暂时隐藏并保存到主场景。** 仅关闭 `GodSpace.CloudSea` 所属体积云组件和蓝图开关，组件同时设为 Hidden In Game，避免天气系统重新设为可见。天空上方的贴图云、海面及云海资产保留。`configure_cloud_sea.py` 的 `CLOUD_SEA_VISIBLE=False` 保持重建时也隐藏。落盘回执：`Integration/Receipts/cloud-sea-hidden.json`；本次未运行测试。

## 复用依据

实际喷泉水面网格 `SM_RomanFountain_WaterWaves` 引用 `MIC_FountainWaveWater`，父材质为 `M_FountainWaveWaterV3`。当前材质已经由 `Tools/Fluids/native_water_surface.py` 接入 Clearwater 原生水面波谱，不能只按历史 V3 脚本判断其现有效果。

旧主神空间海面实际上使用另写的四组 347–883 m 正弦波，80 m 网格，以及另一组三组细波；记录中虽然列了 Clearwater 实例路径，却没有使用其波谱数据。本次改为从喷泉正在使用的 `SourceAssets/ClearwaterWater20260926/waves.json` 生成海面波浪。

从 48 项中按振幅保留 16 项，沿用原方向、相位、角频率、sincos 高度和解析坡度求值；空间放大 100 倍以适应距海面约 1.5 km 的观看位置，时间按空间尺度平方根换算，再乘 1.35，振幅额外乘 2.2。输出波长约 126–354 m，周期约 6.7–11.4 秒。与喷泉原生求值器一样，小于几何解析能力的短波从位移中连续滤除，法线仍保留。生成器及源文件散列在 `Integration/build_reused_ocean_spectrum.py` 与 `Receipts/ocean-reused-spectrum.json`。

沿用现有水纹法线，复用喷泉的 `T_Noises` 作为稀疏浪尖破碎纹理。光滑水面的近景粗糙度改为 0.09–0.13，并在远端连续提高以降低高光闪烁。正式海面实例保持原路径，换用独立的 `M_GodSpaceDistantOcean_FountainSpectrum` 和 `M_GodSpaceOceanFar_FountainSpectrum` 父材质；喷泉的资产、交互和参数保持原样。

此处复用的是实际波谱、波浪求值和已有纹理，不是整个喷泉 Actor 或完整 SingleLayerWater 渲染通路。高空背景继续使用前后一致的 DefaultLit 水面，省去水下折射、焦散、碰撞、水花和互动模拟。近远处共享颜色、远景法线及粗糙度，细节在约 1.8–10.8 km 平滑淡出，12 km 的材质分区不引入另一套着色响应。

## 有界成本

- 海面仍为一个静态网格、两个材质分区。中央网格由 80 m 改为 31.25 m；总三角形由 34,400 增至 167,936，用于承载实际顶点起伏。并非零成本替换。
- 位移在 2.2–3.8 km 淡出，远壳不执行几何波浪；波形法线继续平滑过渡。导入时按波谱振幅上界设置包围盒扩展，避免新增起伏被裁掉。
- 近材质 16 项波谱、4 次二维纹理采样；远材质 1 次纹理采样。没有 CPU Tick、水体交互、碰撞、距离场、海面光追几何或新的全屏水体通路。
- 近景波浪的算术与几何开销增加。没有采集帧时间，不声称帧率提升。

## 云团修改

旧公式把大片高度剖面钳为 1，后续 `(body-cutoff)/(1-cutoff)` 在这些区域恒等于 1，三维噪声被抵消；这会把云顶变成平板。现在保留连续高度剖面，以三维噪声和高度剖面的乘积求密度，不再将云体内部重新钳成整片满值。

主体三维噪声尺度从 4300/5700/2900 m 缩至 1700/2300/850 m，前景边缘尺度改为 520/730/410 m，云团外缘做软侵蚀。降低多次散射补亮并提高遮蔽，留出明暗层次。保留原有天气时钟、风、闪电和原生光照，明确保留 `UsedWithVolumetricCloud`。

仍为一层体积云，主射线近处最多 3 次纹理采样、中远处 2 次；阴影不采样近景细节。本轮不增加射线采样倍率，不添加新云素材。80% 仍是天气分布目标，未测量画面实际覆盖率。

## 制作与交付边界

后台制作入口：Blender 执行 `Integration/author_distant_ocean.py`，随后 UE 的 `Integration/run_background.ps1 -Script produce_fountain_reuse.py -CompileShaders`。增量云修改由 `refine_cloud_lobes.py` 完成，完整重建入口 `build_cloud_sea.py` 同步使用新 HLSL 和散射参数。

本轮不启动编辑器、游戏、截图或性能采样。实际编译保存状态以 `Integration/Receipts/ocean-import.json`、`cloud-lobes-saved.json` 和本轮构建日志为准；脚本和 FBX 制作完成不等于 UE 资产已保存。视觉与帧率由用户进入游戏判断。

2026-09-28 09:50，主制作批次 `fountain-reuse-build` 已完成 D3D12/SM6 材质编译、海面网格导入、正式海面实例换父材质与云主材质增量保存，commandlet 退出码 0。云编译错误列表为空，正式 `UsedWithVolumetricCloud` 保留为 true。没有启动 PIE 或新增截图。

原子 FBX 重导入仍构建了旧距离场，因此 `ocean_mesh_budget.py` 另直接写入 LOD 的距离场/光照 UV 构建设置。后台环境采用与现有喷泉作者脚本一致的 `StaticMeshEditorSubsystem` 临时实例入口；首轮因后台未自动创建该子系统而未保存，后续保存结果记录在 `Receipts/ocean-reused-budget-saved.json`。

09:58，`fountain-reuse-budget-final` 已完成网格 LOD 构建参数修正与保存，退出码 0。本轮必要制作和资产保存全部完成；没有进行运行、视觉或帧率验收。
