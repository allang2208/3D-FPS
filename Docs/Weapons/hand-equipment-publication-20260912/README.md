# 手部装备工作流整理与发布记录

用户于 2026-09-12 接受 3 cm 棕皮革手套薄卷边方案，并授权沉淀技能、归档废案和推送。正式流程见 [手部装备替换标准](../hand-equipment-appearance.md)。

- 将五个试验作者目录的有效脚本、来源记录和本地依赖集中到 `SourceAssets/HandEquipmentAppearance`，去掉从 6 cm/白色旧案生成或恢复的入口。
- 归档 766 个旧试验及历史副本，共 1,091,168,244 字节，包含 11 个退役 UE 包；逐文件移动后 SHA-256 读回一致。`archive_manifest.json` 记录原位置、归档位置、原因和保留入口；有效的原始模型与现用资产未归档。
- 原材质实例的 17 个项目依赖保留。归档前 `dependencies-before-archive.json` 中旧资产没有组外引用；归档后作者目录 `dependency_audit.json` 确认 11 个退役包均已离开 Content，现用依赖不引用它们。
- `validate_authoring.py` 实际重新运行三个 Blender 导出及四个 Python 烘焙步骤，六张作者贴图逐字节一致，原始 Blend 散列未变。结果在作者目录 `authoring_validation.json`。
- 从新目录执行完整 UE 重建与应用，再由新 commandlet 进程回读父材质、起点 0.8899123、皮肤散射 0.18、八张纹理设置和导入源路径，全部通过。导入源已指向新正式目录，可继续 Reimport。`active_asset_manifest.json` 记录重建后的活动包散列。
- 重新运行 2560×1440 DX12 实机捕获，进程退出 0，验收完成；47 通过、2 个与已接受版本相同的粒子过期失败。实际检查空仓换弹和腰射画面，手套长度、薄卷边及皮肤衔接保持。结果及原图位置/散列在 `runtime_validation.json`。没有把 AKM 引用检查称为 AKM 动作实机验收。
- UE commandlet 仍带已有 GameFeatureData 配置错误而退出 1；脚本成功标记和新进程保存回读单独验证。游戏进程也有已有工具插件初始化错误，不属于无错误日志验收；未发现本次材质编译失败或致命错误。
- 手臂技能增加专门参考与触发入口，枪械技能增加路由；个人技能与工程镜像同步。技能校验采用 `python -X utf8 .../quick_validate.py`，避免 Windows 默认 GBK 读取中文文件失败。

发布前检查根目录 `AGENTS.md`、`WORKFLOW.md` 与 `Docs/AssetSetup.md`；只提交本任务脚本、参数、说明和验证记录。现用 UE 资产、原手模、Fab 扫描、贴图、截图、日志和 trash 留在许可本机。并行暂存的 `Docs/AssetSetup.md` 属于改造台任务，本提交不包含它。

推送目标为 `https://github.com/allang2208/3D-FPS.git` 的 `main`，采用普通 `HEAD:main` 推送。最终提交及远端回读记录保留在本机 `Saved/hand-equipment-push.json`，避免把包含自身提交 SHA 的记录递归写入提交。
