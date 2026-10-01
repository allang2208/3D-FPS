# EOTH ADS 准星清晰度调整

范围：EOTH 通用全息瞄准镜的 Common、HK416、M16、M1911、G18、DW715 六种安装版本。沿用各枪挂点、瞄准轴、倍率与配件属性。

原件使用约 4672 个三角面的细线实体准星，加上原图集自发光与加法混合。在小尺寸 ADS 画面中，细线覆盖、贴图 mip、场景曝光和镜片叠层都会影响辨识度。

本次制作：

- 仅替换准星区域，保留镜身、安装座及其材质。新准星位于原准星深度，并居中到既有 SightRear→SightFront 轴；所有瞄准 socket 的位置不变。
- 新准星采用独立平面上的解析圆环、中心点和四个短定位线。像素导数负责抗锯齿与最小可见线宽，避免依赖图集中的细小线条。
- 加入窄暗描边，用于亮背景对比；红色中心点略亮于圆环。EyeAdaptationInverse 使发光受控，避免只靠提高自发光造成糊亮。
- 使用仅限准星覆盖范围的时间响应与透明运动向量，保持窗口透明区域的正常画面处理。
- EOTH 镜片独立采用低不透明度、低反光材质，正视基础不透明度 0.025，掠射最大 0.09，折射率设为 1。其他瞄具及原 HK416 光学材质未批量覆盖。

制作入口：`SourceAssets/EOTHReticle20261001/author_models.py` 与 `import_assets.py`。共享作者实现位于 `SourceAssets/HK416UniversalParts20260930/reticle_geometry.py`、`reticle_materials.py`、`EOTHReticle.hlsl`；原通用配件生成和导入入口已接入同一实现，避免重导后恢复旧分划。

已完成两个光学材质的 SM6 编译，以及六种 EOTH 网格的导入保存。实际资产保存结果记录在 `SourceAssets/EOTHReticle20261001/import_receipt.json`。本次未运行游戏、ADS 截图或验收；最终明暗与清晰度由用户在游戏中确认。
