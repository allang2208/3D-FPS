# AKM 共振二代前握把：后桥与比例修整

用户于 2026-09-13 指出调整后后端镂空、比例不协调，随后明确配件为共振二代前握把（`angled_foregrip`）。本轮仅修改 AKM 这款静态配件。

原适配脚本 `SourceAssets/CantedGripMigration20260911/prepare_akm.py` 将上部几何整体截到枪根空间 Z=-0.0094 m，再增加顶部导轨和单根前侧方柱。切口本身有封面，但后端未接回上方安装座，原来的闭合穿孔轮廓成为开口结构；前端粗柱进一步造成视觉比例失衡。

本轮以原 AKM 静态配件为基线，保留下部斜框、抓握嵌片、三指穿孔区域及装饰细节的原坐标，移除旧转接块，重做连续的上梁、前侧细柱和后侧倾斜支撑。上梁 5.5 mm、前柱约 13 mm 宽、顶部卡边 26 mm 宽，仅为本项目视觉模型参数。不是全模型缩放；原动画、手型和枪根安装矩阵未改。

金属区域改用现有 `/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/M_AKM_Soviet_MountSteel`，金属 UV 重新展开至该贴图组；防滑嵌片保留原聚合物材质与 UV。没有新增外部资产，来源许可沿用原 AKM、M4 及配件资产记录。含原纹理或网格的二进制留在本机。

制作中统一新旧部件的 UV 层名称，避免中文 Blender 新建层与原 `UVMap` 合并后产生空的主 UV；清理原倒角输出中重合的退化碎面，保留表面法线、由 UE 计算切线。

## 作者与接入入口

- `refine.py`：从冻结源移除旧转接结构、制作连续上框、导出 FBX。
- `AKM_ResonanceGrip_Editable.blend`：分件可编辑源。
- `AKM_ResonanceGrip_Export.blend` / `SM_AKM_angled.fbx`：合并导出源及 UE 导出文件。
- `import_asset.py`：仅重新导入 `/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic/SM_AKM_angled`，并绑定既有材质。
- `Before/`、`before-manifest.json`：修改前该 AKM 配件的 Blend、FBX、uasset 与来源散列。
- `authoring.json`、`import_receipt.json`：制作记录与导入保存结果。

运行仍通过 `AKMAttachment::Configure(..., "angled", ...)` 装配，配件 ID、存档、动画分支与其他枪型无需迁移。本轮不重跑旧的批量 `prepare_akm.py`，以免同时覆盖其他握把；这款 AKM 静态网格后续由本目录复现。

按用户规则，本轮只制作、导出与导入，没有执行游戏测试、动画回归或验收渲染。最终外观与使用效果由用户测试。

导入命令行进程退出码为 1，错误摘要为项目已有的 GameFeatureData 资产管理器配置错误；导入脚本已保存目标网格并写出 `import_receipt.json`。该记录仅代表导入保存结果，不代表游戏验收通过。
