# SVD 短弹匣内腔与前后包握修订

## 2026-09-23 整理后的当前入口

旧换弹导出已由 `SVDThumbUp20260923` 替代；当前模型与材质入口为 `SVDRefinedFinish20260923`。本目录的旧制作记录保留其历史日期与验收边界。已经移走的旧导出、自动备份及恢复快照位于 `trash/svd-superseded-20260923/SourceAssets/` 下的同名目录，原路径、散列及保留替代物见 [归档清单](../../Docs/AssetArchives/svd-superseded-20260923.json)。当前所需 Blend、脚本、参数与原素材仍保留；不要直接重跑旧导入覆盖用户已认可的抓握。新 checkout 的恢复方式见 [SVD 发布说明](../../Docs/Weapons/svd-publication-20260923.md)。

后续当前模型／材质源：用户要求参考 PKM 哑光与局部精修后，已在 [SVDMatteDetail20260923](../SVDMatteDetail20260923/README.md) 完成弹匣倒角、底板、独立图集和干湿表面，并同步五套可编辑场景。本目录继续保留手部动作与接触制作参数；不要重跑这里的旧网格导入覆盖后续精修。

用户指出上一轮弹匣抓握仍不贴合、弹匣中间镂空。本目录只修复原厂短弹匣的可见内部和换弹左手，承接 `SVDHandRepair20260923`，保留其他动作、通用配件以及原厂枪托和弹匣的身份。

交付状态：最终模型及 10 条换弹动画已通过现有 UE 桥的互斥批次完成导入、保存；分别见 `model_import_receipt.json` 与 `import_receipt.json`。旧包已备份，没有运行修复后测试。

## 参考与取舍

- 手臂 Skill 的 `references/pose-contact.md`：掌面、拇指对握与四指包裹分别建立；保持 `hand = magazine * grasp`；先松指后退让，骨长、rest、局部平移和权重不变。
- `RifleMagazineGrip20260922/ThumbOppositionV2` 中用户认可的方向：四指在弹匣前缘，拇指从后缘对握。采用后续 `IndexClearanceV4/selected_grasp.json` 的成组手型作为输入，并按 SVD 实际短匣独立调整；V4 自身并非已经完成实机验收的通用模板。
- 武器 Skill 的 `references/extmag-lengthening.md` 与 `MagazineMouthFinish20260919/author_mouth.py`：先区分外壳的装饰开放背面与功能口部，补口缘、内壁和下沉托弹板，不用双面材质或口部平盖代替结构。

## 制作文件

- `prepare.py`、`geometry_input.json`：从当前运行网格对应作者源读取原厂弹匣、真实口缘及原绑定。测量属于本轮必要制作输入，没有运行渲染或游戏测试。
- `author_model.py`、`model_authoring.json`：保留原厂所有外表面、UV0、法线和材质，沿实际 36 边上口制作薄厚边、内壁及约 13 mm 下沉托弹板。新增内部同样刚性绑定到 `WPN_SOCKET_Magazine`。
- `Exports/SK_SVD_Modular.fbx` 与 `SVD_MagazineComplete_Editable.blend`：完整模块化视模的模型导出与作者场景；该模型场景保留修订前动画供制作参考。最终换弹动作在下面五份可编辑场景中。
- `fit_grasp.py`、`grasp_fit.json`：按连续截面建立实际外包络，固定供体的指腹表面区域，分别约束四指前缘、拇指后缘和掌面接触。完整手套顶点、边中点和面心用于制作中的避让约束，不把空腔或冲压凹槽当作手指容纳区。求解残差不是视觉验收结果。
- `author_animations.py`、`authoring.json`：只重做左手第 18–302 源帧间的取匣、持匣、释放与回握；120 Hz 总时长、右手、枪体、弹匣机械轨道及音效/补弹时钟保持。
- `SVD_{base,vertical,canted,prism,angled}_Editable.blend`：五组当前可编辑场景，包含完整弹匣口部与修订后的普通／空仓动作。五组各导出两条 FBX，战术垂直握把继续共用 vertical。
- `import_model.py`、`import_animations.py`、`run_job.ps1`：导入现有运行路径，保留当前材质绑定、骨架、物理资源、动画压缩与 root-motion 设置；经现有批次互斥接入，遇到明确的未保存目标或运行中的 PIE 则保留现场。
- `Before/`、`model_import_receipt.json`、`import_receipt.json`：旧包与实际成功保存的资产回执。模型新内部使用既有 SVD 接口钢材，沿用该材质已有干湿映射。

## 运行目标

模型：`/Game/Weapons/SVDDragunov20260922/Accessories20260923/SK_SVD_Modular`。

原厂普通／空仓：`/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_reload[_empty]`。

四种握把普通／空仓：`/Game/Weapons/SVDDragunov20260922/Accessories20260923/Animations/A_SVD_{vertical,canted,prism,angled}_reload[_empty]`。

所有运行引用保持原路径，无 C++ 修改或编译。只以各保存回执说明接入完成状态。未运行修复后 PIE、游戏、渲染或动作回归，实际观感交由用户测试。
