# SVD 手部动作修复源（2026-09-23）

## 2026-09-23 整理后的当前入口

旧换弹导出已由 `SVDThumbUp20260923` 替代；当前模型与材质入口为 `SVDRefinedFinish20260923`。本目录的旧制作记录保留其历史日期与验收边界。已经移走的旧导出、自动备份及恢复快照位于 `trash/svd-superseded-20260923/SourceAssets/` 下的同名目录，原路径、散列及保留替代物见 [归档清单](../../Docs/AssetArchives/svd-superseded-20260923.json)。当前所需 Blend、脚本、参数与原素材仍保留；不要直接重跑旧导入覆盖用户已认可的抓握。新 checkout 的恢复方式见 [SVD 发布说明](../../Docs/Weapons/svd-publication-20260923.md)。

本目录接续 [基础动作检查](../../Docs/Weapons/svd-basic-contact-review-20260923.md)，修复原厂护木支撑、握匣、拉栓及四种前握把派生动作。制作与接入说明见 [修复记录](../../Docs/Weapons/svd-hand-repair-20260923.md)。

后续用户指出弹匣包握仍不贴合、内部镂空；当前模型及原厂／四种握把共 10 条普通／空仓动作改由 [SVDMagazineFit20260923](../SVDMagazineFit20260923/README.md) 接续，其余 50 条动作保留本目录版本。本目录早期 M4 握匣结果不作为已获用户认可的手型，不重放覆盖新修订。

交付状态：五组各 12 条，共 60 条动画已后台导入并保存到现有运行资产，五批导入均已结束；原包备份与保存记录见 `Before/` 和 `import_receipt.json`。未运行修复后测试。

当前动作作者源为 `SVD_base_Editable.blend` 和 `SVD_{vertical,canted,prism,angled}_Editable.blend`，导出为 `Animations/A_SVD_*.fbx`。保留当前共享 Manny 网格、rest、骨长、权重、枪体、材质和配件，不重新导入模型。

- `prepare_inputs.py`：从 M4 当前 `M4_MAT_reload` 76/60 秒提取完整握匣供体，读取 SVD 实际接口与共享蒙皮。旧 SVD 取的是同 Blend 内 `M4_HK416_reload`，不能继续把它作为当前 M4 换弹供体。拉栓成组手型来自已保存的 ASH12/A762 参考。
- `inputs.json`：固定本轮供体、原姿态、骨架及实际目标网格输入。
- `fit_contacts.py`、`contacts.json`：分别适配护木、短弹匣与拉机柄。调整整手位置/朝向及受限指节旋转，保留掌骨，综合掌面、拇指和四指接触，避免单个指尖最近点主导。壳面优化残差属于制作参数，不是视觉验收结果。
- `author_animations.py`：按缓存的局部旋转重建父子链；指骨局部平移与 scale 使用原 rest，不再从已经修改的父骨和旧子骨世界矩阵反求。肩肘、前臂和辅助骨一同适配；不采用旧派生脚本的分数 twist 叠加。
- `authoring.json`：60 条导出文件及原运行目标路径。原厂 12 条，四种握把各 12 条；战术垂直件继续共用垂直类动作。
- `import_animations.py`、`import_{base,vertical,canted,prism,angled}.py`：按族导入并保存，保留已有骨架、压缩和 root-motion 配置；检测明确目标的未保存修改，逐项备份后写入，按保存回执续作。
- `run_import.ps1`：后台 commandlet 优先；若已有交互编辑器，则转现有项目 MCP 桥接入。两种方式均沿用 `Local\CodexUeMcp-Port-8000` 批次互斥，不关闭或启动交互编辑器。
- `Before/`、`import_receipt.json`：被替换的原包和实际导入保存回执。回执中的散列用于识别本轮源与备份，不代表动作测试通过。

动作总时长和 120 fps 源时钟保持。取匣进入采用现有 AKM/A762 的整手进入方法；源帧 240 压实后，逐指松握，250 起向弹匣外侧让开，268 起回到对应护木/握把，302 完成。右手保留装备 64–94、空仓 310–344 的后拉区间与枪机轨道，释放后外撤再回握。冲刺起止左手渐进回到各自 idle，消除旧制作方法的端点残差。

旧 `SVDCompletion20260923` 与 `SVDAttachments20260923` 动作源保留用于追溯，不能再直接重放旧手指适配脚本覆盖本目录成果。该两目录的模型、材质、配件作者源继续有效。本轮依赖其中的烘焙工具与冲刺轨迹生成函数，日期较旧不代表可移除。

本轮按用户默认规则未新增渲染、压缩读回测试、PIE 或游戏回归。先前检查目录中的图片与数值是修复前证据，不得作为本轮修复后的验收图。实际视觉与手感由用户测试。
