# 骨架枪托局部修整与游戏资源

**2026-09-14 更正：用户明确本模型应作为独立“核心枪托”，上一轮替换 `skeleton` 的做法已撤回到原模型引用。最新独立条目、前段修整和接入状态见 [核心枪托](../../CoreStock20260914/README.md)。本文件以下内容是上一轮制作记录，不能作为当前骨架枪托引用。**

用户在可用性报告后授权“按你建议继续”。本轮保留 seed 91379 的主体，完成局部修整、游戏低模、三张 4K 烘焙贴图及 M4 / AKM / QBZ191 接口版本。原始模型、检查阶段的图片和旧游戏枪托均保留。

## 制作内容

- 局部补建斜支撑与托板下端的缺口、前端肩部异常孔，重新切出前端设计开口。两处主要框架镂空不作为修补目标。
- 批量清理重复/退化数据与多面共边的冗余面，补小边界环；仅对局部接缝和支撑沟槽作有限放松，没有进行全网格体素重建或新的生成任务。
- 未修改三角形恢复原来的角点 UV 和法线；本次精确恢复 356,996 个源三角形的角点数据。修整细节见 `repair_operations.json`。
- 从修整母版制作约 5 万面游戏低模，烘焙 4096 × 4096 BaseColor、MetalRough、切线 Normal。导出阶段另清理减面产生的无效网格数据。
- 游戏导出 UV0 使用新烘焙图集，UV1 保留来源 UV，UV2 投射各枪机匣涂层，避免结构法线和切线基准使用不同 UV。Normal 在 UE 中翻转绿色通道。

## 逐枪版本

| 枪型 | 作者导出三角面数，含转接 | 接口制作 |
| --- | ---: | --- |
| M4 | 50,916 | 既有枪托挂点 + 环形过渡，主体前缘后移以容纳过渡段 |
| AKM | 52,132 | 既有 AKM 独立挂点 + 通孔机匣尾盖 + 环形过渡 |
| QBZ191 | 51,292 | 既有枪根坐标和专用肩台，网格预变换到 WPN_root 空间 |

主体作者长度为 20 cm，安装原点取前端开口中心，+X 指向托板。各枪的尺寸、连接方案是基于现有装配资料的制作结果，尚未通过本轮游戏画面确认。转接具体参数与资源路径见 `variant_authoring.json`。

四个材质槽为 StockMetal、StockPolymer、StockRubber、StockAdapter。金属分别使用 M4 当前 Phong 转换、AKM 机匣 PBR 取样区、QBZ191 当前涂层；聚合物和橡胶沿用烘焙色图，橡胶保留较高粗糙度。新转接不采样无关的主体结构法线。Blender/GLB 金属为工作材质，最终逐枪涂层由 UE 导入脚本建立。

## 文件与接入

- `SkeletonStock_Repaired_Master.blend`：修整母版，包含隐藏的冻结来源对象。
- `SkeletonStock_Game_Low_Editable.blend`：减面与烘焙编辑源；游戏导出的清理和接口步骤继续由下列作者文件完成。
- `{M4,AKM,QBZ191}/SkeletonStock_Game_Editable.blend`：最终逐枪作者源。
- `{M4,AKM,QBZ191}/SM_SkeletonStock.fbx`：UE 静态网格导入文件；同目录 GLB 供通用编辑查看。
- `Textures/`：三张 4K 烘焙贴图。
- `repair_master.py` → `build_game.py` → `author_variants.py` → `import_assets.py`：制作和导入入口；均不启动游戏或验收渲染。

新 UE 目录：`/Game/Weapons/ReferenceStock5080/Refined91379/{M4,AKM,QBZ191}/SM_SkeletonStock`。已有 `/Game/Weapons/ReferenceStock5080` 打包目录覆盖此子目录。

`Source/FPSGAME/Weapons/SkeletonStockVisual.cpp` 和 `QBZ191Attachments.h` 将 `skeleton` 指向这组三枪资源，沿用角色、改造预览、库存图标和掉落的共用装配入口。配件 ID、属性、存档、原厂枪托恢复和独立 `qr_performance` 高性能后托保持原逻辑。本次修改前的两份源码快照在 `Before/`。

## 当前交付边界

模型制作、导出、三枪 UE 资源保存与接入源码修改均已完成。最终保存路径见 `import_results.json`，日志有三条 `STOCK_REVISION_SAVED` 及 `STOCK_REFINED91379_IMPORT_COMPLETE`。

2026-09-14 用户保存并关闭编辑器后，`Tools/Build/Build-Editor.ps1` 完整依赖图构建成功，重链接普通名称的 AutoFootstep、AutoFootstepEditor 和 FPSGAME 模块，消除了此前导入启动阶段的 AutoFootstep 重复类阻塞。构建回执为 `build_editor.log`，引擎构建日志为 `Saved/BuildEditor/build-20260914-000101.log`。

最终导入脚本完成且资源保存成功，但 commandlet 因项目已有 GameFeatureData 资产管理器配置错误退出 **1**；没有将该非零退出码写成完全无错误。错误与 Python 导入保存结果分开记录，见 `import_assets.log`。本轮不扩大修改项目 GameFeature 配置。

`ImportHost/StockAssetImport.uproject` 是启动冲突期间的临时纯资源导入入口，初次尝试停在材质编辑属性接口，已修正导入脚本，最终使用原 FPSGAME 工程完成导入。`ImportHost/Content` 是指向正式 `D:/FPS3D/FPSGAME/Content` 的目录连接；解除该连接的清理动作被自动审批拒绝（工具返回 `blocked by policy`），连接仍保留，未删除正式资源。今后在编辑器关闭时可用 `continue_integration.ps1` 重新构建和导入，无自动测试。

按用户全局规则，本轮未追加网格验收、渲染、UE 装配、动画、存档或性能测试，交由用户测试。上级 `UsabilityReview` 图片均是修整前版本，不能作为本轮修整后的预览。导入/导出过程中产生的警告保留在各日志中，不宣称最终拓扑或视觉已经验收通过。
