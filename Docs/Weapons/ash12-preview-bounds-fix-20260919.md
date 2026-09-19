# ASH-12 通用配件显示与改造拖动故障

## 原因

九个 ASH 通用配件网格的序列化 `ExtendedBounds` 损坏，包含零值和极大异常值。资产仍可加载且三角面数据存在，但错误边界影响显示裁剪；改造预览 `UM4GunsmithWidget::SyncStudioPreview()` 使用相同边界计算整枪中心和正交视宽，又放大为拖动、缩放异常。四种瞄具、四种前握把及 LPVO 活动环均受影响。原始 FBX、ASH 托腮板和战术消音器的边界正常。

之前的命令行 Interchange 导入留下了运行时快速构建模式。UE 的 `FStaticMeshRenderData::Cache()` 在 `bDoFastBuild` 分支构建顶点缓冲后没有填充整个网格的 `Bounds`。随后 `finish_mesh_build.py` 在 NullRHI 编辑器重建并保存，`UStaticMesh::CalculateExtendedBounds()` 使用异常渲染边界，最终把错误值写入资产。仅看导入或保存成功日志不能发现这一问题。

重导入能修好 `ExtendedBounds`，但保留了快速构建标记；切换构建格式只会再次走相同错误路径。运行排查发现 `FStaticMeshRenderData::Bounds` 仍有零值、极大值，距离场的 `LocalSpaceMeshBounds` 随之错误；从全息切到红点时开始出现 GPU 矩阵转换及 `InverseFast` 错误。必须清除 `bDoFastBuild` 并绕开旧缓存，才能完整重建。该表现与 [Epic 关于快速构建边界的技术支持记录](https://forums.unrealengine.com/t/static-mesh-bounds-calculation-issue-with-bdofastbuild/2664547) 一致；具体引擎分支已在本机 5.8 源码中定位。

## 修复

- 保留现有源模型和材质绑定，在启用 RHI 的完整编辑器从原 FBX 重新导入九个网格。
- 保留导入的分离法线，按 UV0 使用 MikkTSpace 重建切线；清零正负边界扩展，让边界来自真实顶点。
- `UASH12AttachmentAssetTools` 为 Python 提供受保护的快速构建标记读写，以及静态网格／距离场编译完成后的检查。导入后清除 `bDoFastBuild`，使用完整导入网格构建路径。
- 这九个网格采用高精度切线和 UV 缓冲格式，避开此前损坏的 DDC 键，重建渲染网格和距离场。几何、UV 坐标、分离法线及材质绑定保持原样。保存前同时确认资产边界、渲染边界、距离场包围范围。
- 修复前文件备份到 `SourceAssets/ASH12UniversalAttachments20260919/BeforeBoundsRepair/`。
- 最终构建入口改为从 FBX 重建；导入和最终构建均拒绝 NullRHI、commandlet 和 PIE，防止再次执行已知有问题的保存路径。
- 拖动输入仍使用所有枪型共享的 `SM4PreviewSurface`；本次没有给 ASH 添加独立灵敏度或特殊旋转补偿。

## 当前证据

九个网格修复前的 `bDoFastBuild` 均为 true，修复后均为 false。重建网格的各轴边界与 Blender 独立读取的 FBX 顶点范围一致，误差小于 0.02 cm；保存前已等待这九个模型的渲染及距离场编译完成，并检查其有效性。正式模块构建成功：`Saved/BuildEditor/build-20260919-222937.log`。

资产修复明细：`Saved/ASH12PreviewFix/repair.json`；最终修复日志：`Saved/ASH12PreviewFixImportedMeshRepair.log`；作者回执：`SourceAssets/ASH12UniversalAttachments20260919/import.json`。此前 `Saved/ASH12PreviewFixRuntime.log` 的 67 项检查通过仅覆盖交互和资产边界，后续增加了对渲染数据和距离场的检查，不能把首轮结果等同于最终结果。

最终运行排查入口为 `-ASH12SightCapture -ASH12PreviewFixAudit -ColdSteelProfile=ASH12SightAudit_PreviewFix_20260919g`。它在重新启动的独立进程使用独立存档，只覆盖通用配件构建模式／边界／渲染数据／距离场、预览、装卸、ASH/M4 的实际 Slate 鼠标拖动与滚轮，以及新增托腮板的显示。

最终日志 `Saved/ASH12PreviewFixAcceptedFinal.log`：`ASH_PREVIEW_FIX: COMPLETE checks=112 failures=0`，渲染矩阵错误及 ensure/fatal 匹配均为 0。四组瞄具与握把均显示；ASH 与 M4 对同样的鼠标拖动和滚轮输入产生相同的旋转与缩放变化，旋转状态在后续预览刷新中保留。

距离场使用单精度坐标，与双精度资产边界比较时允许 0.001 cm 舍入误差；最终 15 个样本的最大实测差为 `2.38418579e-7 cm`。该容差同时用于保存前检查及运行排查。

界面记录位于 `Saved/ASH12PreviewFix/ash-pair-0.png` 至 `ash-pair-3.png`、`ash-dragged.png` 和 `m4-dragged.png`。本次结果不等同于 44 条动画、天气或全部枪械功能验收，其余体验由用户测试。
