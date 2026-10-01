# 枪械表面制作与当前绑定

本目录包含 WS1 基础制作、WS1.1 前期方案，以及九枪逐枪修订。当前范围与发布边界见 [阶段发布](../../Docs/Weapons/weapon-surface-animation-publication-20261001.md)。

公共仓库提供作者 Python/PowerShell、HLSL、文档及精选小型参数/绑定清单。`Input/`、`Bake/`、`Before/`、日志、采样图、原纹理和 UE 生成资产留在本机：这些含来源资产及密集派生数据，不是脚本默认下载的公共依赖。既有来源署名和授权边界沿各枪原记录保留。

## 当前制作链

- A762：基础 WS1 → Refine06；最新几何接 Continuous07、ReceiverGrip08、GripClearance09。旧整枪 FBX 不能直接覆盖当前枪体 UV/接口。
- ASH12：分区私有图与纹理输入 → Refine02；保留特殊 UV 和天气映射。
- SVD：基础适配图 → MagazineSatin02 → Refine03 → Refine04。后两版沿前序结构制作，目录编号较旧不表示可删。
- AKM：Refine01 创建适配图和实例 → Refine02 更新同路径配方 → DrumFinish03 修正聚合物鼓壳。`current_surface_bindings.json` 是发布绑定，R01 资产名不代表仍用旧参数。
- HK416、M4、M16：各自 Refine01 的 `capture_inputs.py` → `produce.py` → `apply_finish.py` → `finalize_records.py`。M4 还需 `read_source_contracts.py` 提取本地作者 PBR 通道；其他枪不能套用 M4 的旧 Phong 转换。
- PKM、201：各 Refine01；PKM 当前绑定另写入原作者目录的 `current_surface_bindings.json`，201 写入 `LMG20120260927/Material21/bindings.json`，旧导入入口会沿用。

恢复时先具备已授权的本地原资产及当前网格，再按各版本文档读取输入、制作和保存；不要仅凭目录顺序批量执行全部脚本。已完成回执可供同一次生产续存，源资产改变后需重新采集和制作。`WS11/` 仍是前期候选参数和共享函数接口方案，不是已安装的全量母图合并。

`run_ue.ps1` 在本项目编辑器已运行时使用现有批次桥，否则使用无界面 commandlet。M4/M16 的 `run_finish.ps1` 检查共享 Content 的占用。实际保存冲突需要保留现场并在当前对话处理，不终止其他编辑器或另开进程覆盖。

旧完整动画和私有材质原图保留用于重制/回退；本轮不清理 Cook 目录，也不以文件计数宣称性能收益。检查/截图/运行测试仅在用户明确要求时执行。
