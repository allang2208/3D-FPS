# G18 全息瞄具镜窗遮罩修复

用户反馈 G18 全息瞄具镜窗黑色、不透明。本次只修正 G18 全息镜的材质绑定和后续制作入口。

## 原因与改动

原全息镜将外壳与镜窗面放在同一个 `M_HoloBody` 槽，依赖原材质 `M_HoloBody` 的 UV0 贴图 Alpha 和 Masked 混合模式保留光学开口。G18 的底座修复导入脚本将该槽直接绑定到不透明 `M_G18_AttachmentFinish`，因此连镜窗也被填成深色金属。分划属于独立 `M_HoloReticle` 槽。

- 新建 G18 专用 `M_G18_HoloBodyMasked`，复制本枪现用配件钢材／雨水图，恢复原全息镜的 Alpha 输入、UV 通道和裁切阈值。
- 实际全息镜的 `M_HoloBody` 槽使用新材质，`M_HoloReticle` 槽使用原有 Masked 自发光分划。
- 将新材质加入 `DA_G18_WetMaterials`，雨水动态材质继承同一遮罩。
- 全量 G18 导入和旧配件修复导入均调用同一个制作助手，避免重导入再次用不透明金属覆盖镜窗。

本次沿用原瞄具的遮罩开窗方案；未增加场景捕获、折射或新玻璃网格。镜体、安装座、UV、插座、AimCenter、ADS、动画和属性均未修改。共享 M4／M1911 材质不改写。

## 制作与保存

- 制作助手：`Tools/Weapons/g18_holographic_material.py`。
- 单次接入：`SourceAssets/G18HolographicTransparency20261005/apply_materials.py`。
- 后台入口：同目录 `save_background.ps1`，仅无编辑器／commandlet 占用时运行；已有编辑器使用现有 MCP 互斥桥执行同一 Python 脚本。
- 保存回执：同目录 `save_receipt.json`，逐项记录保存结果及修改前后槽绑定。
- 修改前包：同目录 `BeforePackages/`。
- 运行网格：`/Game/Weapons/G18/Integrated20260929/Attachments/SM_G18_holographic`。
- 新材质：`/Game/Weapons/G18/Integrated20260929/Materials/M_G18_HoloBodyMasked`。

三个目标资产已保存，回执状态为 `materials_bound_and_saved`。保存前实际槽绑定确认：镜体为不透明 `M_G18_AttachmentFinish`，分划已经使用正确的 `M_HoloReticle`；本次保留分划，仅修复镜体开口。

首次后台 commandlet 在自动 SDK 查询等待已有构建锁时尚未执行制作脚本，因此结束本任务进程，并为后台入口增加引擎支持的 `-Multiprocess`。随后发现工程已有交互编辑器运行，实际保存改为通过现有 `mcp_call_codex.ps1 -PythonScript` 互斥桥完成，结果见 `save-mcp-01.txt`。未改动其他构建或由本任务启动／重启编辑器。

未运行游戏、截图、渲染、自测或验收。资产保存与实机观感分开记录；效果由用户测试。当前游玩实例若仍持有旧雨水动态材质，重新装备或拆装全息镜以重建配件实例。
