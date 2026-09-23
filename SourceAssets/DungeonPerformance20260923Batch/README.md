# 地牢性能资产制作（2026-09-23）

当前采用恢复后的 RT／Lumen 光照。运行源码、作者脚本与资产制作结果见 [完成记录](../../Docs/Performance/dungeon-performance-completion-20260923.md)。这里的脚本用于明确要求的制作，不自动启动游戏或性能采集。

- `mesh-targets.json`：此次实际场景网格的包路径清单，只有名称，没有网格、材质或第三方数据载荷。
- `apply_assets.py`：每次最多构建六个兼容高面数刚体；设置 Nanite、显式切线、完整回退，并修正两个静态 ASH-12 弹匣材质用途。依赖已构建的 `PlazaInstanceTools.build_nanite_data`。
- `finish_materials.py`：同一制作批次内保存 Nanite 使用产生的材质修改；不能借此保存来源不明的脏资产。
- `build_editor.ps1`：编辑器正常关闭后在后台构建 Editor 目标；引擎路径采用本机 `E:/Program Files (x86)/UE_5.8`，其他机器按实际安装修改。
- `underground-import-nanite.patch`：本次对楼梯导入脚本的局部改动。该脚本主体由独立任务制作且尚未发布，补丁保留本次贡献；应用前需要对应版本的完整导入脚本，不能单独运行补丁制作楼梯。

资产需先从合法本机内容恢复。制作可通过适用的后台 Python commandlet 执行；若已有编辑器会话，则经 `Tools/AssetPipeline/mcp_call_codex.ps1` 的批次互斥执行，不能另开进程覆盖已加载资产。重复调用 `apply_assets.py`，以本批 `Receipts/assets.json` 的 `remaining=0` 为完成标记，再在同一制作上下文运行 `finish_materials.py`。每次调用应保留独立的桥输出文件；已退役的固定 PythonNodeId 批次脚本不再使用。

`Before/` 是按项回溯的原文件备份，`Receipts/` 是本机制作与构建记录，均不公开。已有回执只适合继续同一批次；重导或变更源资产后不能依据旧的 `remaining=0` 跳过制作，应为新制作另存旧回执和备份，使用新批次记录。历史回执不证明当前内容仍满足当时设置。

本批完整 Content、第三方素材、uasset、日志和二进制留在本机。源码仓库不是可直接运行的完整工程备份；不要用 `Before/` 整目录覆盖其他任务的修改。
