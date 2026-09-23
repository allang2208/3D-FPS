# PSO 接缝透空修复（2026-09-23）

## 2026-09-23 整理后的当前入口

旧换弹导出已由 `SVDThumbUp20260923` 替代；当前模型与材质入口为 `SVDRefinedFinish20260923`。本目录的旧制作记录保留其历史日期与验收边界。已经移走的旧导出、自动备份及恢复快照位于 `trash/svd-superseded-20260923/SourceAssets/` 下的同名目录，原路径、散列及保留替代物见 [归档清单](../../Docs/AssetArchives/svd-superseded-20260923.json)。当前所需 Blend、脚本、参数与原素材仍保留；不要直接重跑旧导入覆盖用户已认可的抓握。新 checkout 的恢复方式见 [SVD 发布说明](../../Docs/Weapons/svd-publication-20260923.md)。

当前状态：4 个运行网格、8 张补全纹理已通过后台 commandlet 导入保存，`import_receipt.json` 的 `completed=true`。没有启动交互式编辑器或运行游戏。

后续用户要求的 PSO 表面升级已在 [PSOMatteFinish20260923](../PSOMatteFinish20260923/README.md) 完成；当前网格使用该轮专用哑光干湿材质，本目录保留接缝几何与补全图集的制作记录。

用户报告检视时镜筒衔接处透出背景。本次检查定位到材质分区：最初拆分脚本只按“薄、圆、位于光轴附近”识别镜片，误把环形台肩和接缝金属面一起分入 `ScopeLens`。这些面没有丢失，却使用了透明玻璃材料；原来的表面烘焙也排除了这批面。

## 制作结果

- 从当前 SVD 哑光精修及三款 PSO 改造件的可编辑源继续处理，不重新生成枪体。
- 逐个几何岛判断其三角面是否覆盖光轴。340 个环形机械三角面重新使用既有镜体材料；真正的 15 个镜片三角面保留玻璃材质。
- 不移动顶点，不补死光学通道。保留现有 UV 坐标、角点法线、骨骼与权重，保留已完成弹匣、动作和安装座。
- 复用保存的涂层作者图，仅为这些金属环补烘焙 4K BaseColor/ORM。SVD 使用自身镜筒表面，AKM/A762/PKM 使用各自涂层；原结构法线不改。更新同名纹理资产，使已有干／湿材料都能使用完整图集。
- 六份 `SVDMatteDetail20260923/SVD_*_Editable.blend` 和三份 `PSO1Russian20260923/PSO1_*_Editable.blend` 已同步正确分区。导入 FBX 与补全后的纹理位于本目录 `Exports/`、`Textures/`。
- 最初 `SVDDragunov20260922/Scripts/separate_svd_parts.py` 已加入光轴面覆盖条件，避免将环形金属误判为玻璃。沿用旧分区中间源重新制作时，应在最后运行本目录修复步骤；不要重新导入旧目录遗留 FBX 覆盖本修复。

## 后台接入

`run_job.ps1 -Script import_repair.py` 在现有批次互斥下导入四个现有资产。保持资产路径和当前材质槽名称／绑定，保留 SVD 骨架、物理资产、后处理动画类和各款改造件瞄准 Socket。脚本在目标包未保存、PIE 或其他项目 commandlet 运行时保留现场。

运行资产：

- `/Game/Weapons/SVDDragunov20260922/Accessories20260923/SK_SVD_Modular`
- `/Game/Weapons/PSO1Russian20260923/AKM/SM_PSO1_AKM`
- `/Game/Weapons/PSO1Russian20260923/A762/SM_PSO1_A762`
- `/Game/Weapons/PSO1Russian20260923/PKM/SM_PSO1_PKM`

## 用户要求的定向检查

`authoring.json` 记录九份作者源中重分区前后顶点、拓扑、UV、角点法线及权重散列相同。`export_checks.json` 记录重新读取四个导出 FBX 后，每套均为 340 个不透明接缝面、15 个玻璃面。`texture_checks.json` 记录纹理尺寸均为 4096²，显著像素变化约占各图集 1.0–1.7%，只补做接缝区域及烘焙边缘。

`seam_winding_checks.json`：位置焊接仅在分析副本中进行，238 条环与镜体相接边的绕序均一致。保留的两个内缘边界分别位于镜筒重叠区域；对各连接处前后约 2 mm、32 个圆周方向进行 1,088 条外侧射线采样，均有外壳遮挡。采样避开环面完全共面的数值歧义，不把模型分析等同于游戏画面验收。

`import_receipt.json` 是实际运行包保存凭据，须以其中 `completed` 和逐包 `saved` 为准；源文件制作成功不等于 UE 已导入。没有启动交互式 UE、PIE 或游戏，没有追加动作／枪匠回归及画面验收。

改动前的对应作者源和运行包保存在 `Before/`。来源仍为 LeroyCake SVD 的 CC BY 4.0 派生模型，保留项目原署名与许可。
