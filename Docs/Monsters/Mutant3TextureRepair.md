# 突变体-3：贴图排查与修复（2026-09-23）

当前版本与恢复顺序见 [突变体发布入口](Mutant3FeralPublication20260923.md)。本文保留阶段记录；其中 before/baseline 快照及已退役独立手臂求解已按归档清单移至 trash。

用户反馈上次手臂修订后贴图没有成功渲染。本次只处理材质与预览输出，保持已保存的手部模型、绑定和飞扑动作。

## 查到的问题

1. 原 `inspect_refined_export.py` 用 `BLENDER_WORKBENCH` 的对象纯色模式输出动作图，而且通过 `from_pydata` 重建检查用网格时只传递顶点和面，没有保留 UV 与材质。该图用于查看手臂形变，本身不会显示贴图。
2. 飞扑 FBX 使用 `path_mode='STRIP'`，没有携带贴图；在独立目录重新打开时，四张贴图都被解析为不存在的同名文件，尺寸为 0×0。原 Blender 作者文件内的贴图仍已打包，原模型与实际 FBX 的 UVMap 均存在。
3. 从正式 Content 复制出的当前模型材质槽实际指向 `M_Mutant3_Meshy`，并非此前另行制作的 StyleV1 实例。四张原始贴图可正常加载，颜色为 2K、法线为 2K、粗糙度与金属度为 4K；骨骼网格用途已启用。但材质只连接旧版 BaseColor / Normal / Roughness / Metallic，`Front Material` 未连接，而正式项目开启了 Substrate。

## 修复内容

- 保留当前四张原始贴图和旧输出连接，补充 `MaterialExpressionSubstrateShadingModels`，将原输入接到 Default Lit 表面，再连接到 Substrate `Front Material`。不替换为另一套皮肤，不修改共享感染材质。
- 给独立 FBX 目录补齐其引用的四张原始 PNG；今后飞扑导出改为 `COPY` 并嵌入贴图。
- 新预览从实际导出的 FBX 取蒙皮结果，使用 `new_from_object(... preserve_all_data_layers=True)` 保留 UV，连接当前正式材质对应的颜色、法线、粗糙度和金属度，使用 Eevee 输出带贴图的动作图。
- 原检查入口默认交付带贴图的 `refined_export_arms.png`；白模图另存为 `refined_export_arms_clay.png`。后续再次运行检查时不会默默回到白模交付。

## 交付与范围

作者目录为 `SourceAssets/Mutant3Khaimera20260923/texture_fix/`。`ue_material_inspection.json` 记录材质槽与输入引用，`material_repair_state.json` 记录保存和安装状态，`before_content/` 保留正式材质修改前副本。

预览为 `refined_export_textured.png`，可编辑场景为 `Mutant3_Textured_Preview.blend`，四张贴图已打包；`texture_preview_delivery.json` 记录输入和输出。图片已查看，皮肤、眼睛、裤子和手部贴图能够显示。这是 Blender PBR 预览，不是 UE 游戏截图。

`M_Mutant3_Meshy.uasset` 已正式保存。准备写回隔离作者工程的产物时发现主工程已重新运行，因此没有覆盖已加载文件，改由现有编辑器桥执行同一修复；首次保存因 PIE 未结束而失败，结束已有 PIE 后仅保存内存中已修复的材质，返回 `MUTANT3_MATERIAL_INSTALLED 1 material`。最终状态为 `installed and saved in active production editor`，记录见 `material_repair_state.json` 与 `repair-save-live-02.txt`。

先前启用渲染的 commandlet 停留在引擎默认材质的 SM5 着色器编译阶段，未进入资产脚本；已结束本任务该进程，改用 NullRHI 完成隔离材质图落盘。后续正式接入通过实际主工程完成，但保存结果仍不等同于游戏画面验收。

未主动打开交互式编辑器或启动游戏；为完成保存结束了主工程已有的 PIE。本次没有重导入模型、骨架或动画，游戏内观感仍待用户确认。
