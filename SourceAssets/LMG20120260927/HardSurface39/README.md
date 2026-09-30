# 201 HardSurface39

用户要求修整红圈小件和凹凸硬表面，并在修改后检查。制作记录：`../../../Docs/Weapons/lmg201-hard-surface-20260929.md`。

当前作者模型 `LMG201_HardSurface39.blend`；完整运行导出 `Exports/After_Body.fbx`；底座 `Exports/After_BipodBase.fbx`。以 `delivery.json` 的保存状态和散列为准，不把源 FBX 或安装脚本的存在当成已接入。

作者流程：

1. `collect.py` 在后台读取运行枪体及独立脚架资产；`extract_original.py` 从 R38 编辑源提取未改几何。
2. `fair_panels.py` 只拟合连续大平面，固定边界及护木握持纹区域。
3. `model.py` 读取 R38 的有界建模帮助函数，重做前端规则件、导轨、紧凑底座，并保留旧槽共用件。
4. `materials.py` 建立私有涂层和局部表面遮罩；`install.py` 保存原路径及修改前副本，合并天气表。
5. 本轮用户明确要求检查，因此执行 `check_assets.py` 与 `check_saved.py`。它们不是后续普通修改的默认测试步骤。

后台命令入口 `run_background.ps1` 使用现有 UE 批次互斥；不主动开 GUI，不覆盖另一个已运行 UE 进程。安装后由 `Exports/After_*.fbx` 完成定向离线灰模检查。没有修改原生代码、原动作或脚架腿。原始备份在 `Before/` 与 UE `/Game/Weapons/LMG201/HardSurface39/Previous`。

`saved_front.png`、`saved_front_under.png`、`saved_receiver.png` 是实际保存资产的离线局部灰模，包含当前准星与脚架组件；它们不表示实机动作或材质已获认可。
