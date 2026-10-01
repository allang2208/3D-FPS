# G18 配件修复源

本目录修复扩容弹匣壳体绕序、全息及全景红点底座接触。

沿用 `../G18Integration20260929/README.md` 的用户本地模型和项目附件来源，不新增外部模型、动画或下载资源。

当前作者链：Blender 后台执行 `author_repair.py` → Python 执行 `author_icons.py` → 在现有编辑器互斥批次或无编辑器时的后台 commandlet 执行 `import_repair.py`。这一步位于最初 G18 作者链之后；不要只重跑最初 `author_parts.py` 并省略修复步骤。

`source_shape.py` 读取制作所需的壳体连接和上下安装面；`source_shape.json` 是取形数据，不是实机测试记录。`Exports` 保留修正版 FBX 和可编辑 Blend，`BeforePackages` 保留本次替换前的三个包。

`import_receipt.json` 记录实际保存的资产。详细改动见 `../../Docs/Weapons/g18-attachment-repair-20260930.md`。未运行游戏、预览截图或额外验收。
