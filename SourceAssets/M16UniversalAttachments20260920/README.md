# M16A2 通用配件作者工程

最终选择与恢复顺序见 [M16 发布记录](../../Docs/Weapons/m16-publication-20260920.md)。本目录的瞄具、后握把、普通弹匣换弹、快速近战和枪托输出分别由后续目录修订；保留本目录的上游 Blend。`AuthoringRecovery` 尚有 8 个正式包引用的依赖，详见发布清单，勿整目录删除。

本阶段说明与历史交付状态见 `../../Docs/Weapons/m16a2-universal-attachments-20260920.md`。本目录只包含本次 M16 适配，不覆盖通用源件。

- `sources.json`：24 个通用源网格及实际材质／插座绑定。FBX 导出关闭碰撞辅助网格。
- `authoring.json`：M16 几何接口、骨架和已有完整抓握源；源动作查看采用现有 VRE 抓握图和 M4 DrumContact 接触图。
- `models.json`、`M16_CommonAttachments_Editable.blend`、`Meshes/`：25 个适配网格。根空间、瞄具空间、枪口空间与弹匣绑定空间分别明确记录。
- `M16_*_Animations_Editable.blend`、`Animations/`、`animations.json`：68 条目标骨架动画，120 Hz 导出；保留 M16 拉机柄空仓尾段。
- `Textures/`、`coating.json`：原机匣金属区域的涂层图块与物理尺度。
- `Icons/`：7 个实际模型的正式 UI 图标、可编辑摄影场景和来源清单；不是验收截图。
- `import_receipt.json`、`icon_install_receipt.json`：实际保存的资产、材质槽及长度回执。
- `catalog.json`：只更新 M16 对象后的通用目录；基础枪械数值不改。

作者入口依次为 `export_sources.py` → `read_authoring.py` → `author_models.py` / `author_coating.py` / `author_animations.py` → `import_assets.py`。UE 脚本通过项目 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript <脚本>` 的批次互斥执行。`publish_catalog.py` 只替换 M16 的 JSON 对象。`render_catalog_icons.py` → `install_icons.py` 制作并发布图标。`install_runtime.py` 是本轮源码接入记录，不能对已经接入的源码重复运行。

同造型改造件保留现有共享图标，M16 原厂件及自身轮廓不同的扩容弹匣提供专属覆盖。材质与动画均在 M16 私有目录，不改其他枪械母资产。

未执行游戏测试、额外检查或验收渲染，由用户实机测试。

构建状态：热编译因编辑器退出而取消；后续常规构建被 `VoxelBuildComponent.cpp:298/309` 的既有 API 调用错误阻断，未链接出新模块。M16 编译单元未报错，体素模块保持原样。见 `build_editor.log`；不要将资产保存完成表述为运行接入已生效。
