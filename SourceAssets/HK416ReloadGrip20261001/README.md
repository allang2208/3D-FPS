# HK416 换弹抓握制作源

`author_standard.py` 在弹匣壳坐标中注册已认可的 M4／AKM 手型，并保留普通与扩容共用上段抓握。`author_drum.py` 冻结掌腕，只聚拢与卷曲四指。两者的输出为当前原生动画的局部骨轨道，不替换骨架、蒙皮或机械动作。

`HK416_ReloadGrip_Editable.blend` 包含完整的 20 条换弹动作；`Inputs/*__full.json.gz` 保留本次制作前完整原生姿态。

已有编辑器时，经 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript SourceAssets/HK416ReloadGrip20261001/install.py` 保存。脚本保护 PIE、未保存目标包和制作期间的文件变动，按 `delivery.json` 的明确保存边界续接，并同步现有握把 Profile。

`PackageStaging` 是本次共享 Content 占用期间的独立包副本，写入目标动画／Profile 为普通文件，非目标目录仅作为只读依赖映射。其保存回执为 `staged_delivery.json`，不等于主库已全部接入。编辑器彻底退出后可用 `publish.py` 发布；编辑器保持打开时应结束 PIE 并用现有桥保存。

未运行游戏、测试、预览或渲染。最终状态以 `delivery.json` 和 `Docs/Weapons/hk416-reload-grip-20261001.md` 为准。
