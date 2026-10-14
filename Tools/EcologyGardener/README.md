# 园艺师当前制作入口

当前服装修订为 **V02**，源文件和交付回执位于 `SourceAssets/EcologyGardener20261014/V02`。

- Blender 后台制作：`author_v02.py`。
- UE 后台导入及保存：`import_v02.ps1`，通过共享批次互斥执行 `import_v02.py`。
- UE 已运行时：通过项目 `Tools/AssetPipeline/mcp_call_codex.ps1` 执行 `import_v02.py`；保留正在运行的 PIE 和未保存资产。
- 当前外观蓝图入口保持 `/Game/Monsters/EcologyGardener/BP_EcologyGardener`，新网格/材质位于其 `V02` 子目录。

旧 `author.py`、`import_assets.py`、`build_and_import.ps1` 属于 V01 恢复配方，不用于当前版本重导。V01 与 V02 均保留研究员身体、骨架、动作及 231 个 FR 修形。

本轮仅外观资产修改，无新增 C++。不自动启动交互编辑器、游戏或验收渲染。
