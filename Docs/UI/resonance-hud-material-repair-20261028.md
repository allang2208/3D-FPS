# 山鸣／疾律 HUD 材质连接修复

## 用户报告与证据

用户报告阿尔卑斯剪影在怪物和训练靶命中后均不显示。预期是装备山鸣时0层暗显，三次满弓有效命中后按比例点亮。

当前源码已将山鸣装备实例接到HUD入口；箭矢命中通道同时接纳存活敌人和`AFPSPracticeTarget`。这些源码条件不等同于本次实机已重现成功。

`Saved/Logs/FPSGAME.log`在2026-10-28 04:04:16 UTC明确记录：`M_MountainEcho_AlpineHUD`的PCD3D_SM6编译失败，游戏改用默认材质；具体错误为两处`Missing ComponentMask input`。

源导入脚本将Custom输出连接到ComponentMask的`Input`名字，却没有处理连接返回值。当前引擎此节点使用未命名的第一个输入。之前的NullRHI导入可以保存资产，但没有对应图形平台的材质资源，不能据此判断着色器可用。疾律复用了该图生成段，存在同源故障。

## 修复范围

- 两个HUD作者脚本改用未命名的第一个输入，检查颜色/透明度连接返回值，保留原贴图、参数和玩法。
- `ResonanceHUDRepair20261028/repair_materials.py`记录已保存材质的节点与断线后，按原作者脚本重建这两个HUD图，复用已保存贴图，不改变伤害、目标规则或叠层条件。
- 阿尔卑斯材质实际遗留8个节点、2个Custom，其中两个输出Mask输入均为空。当前引擎的批量删除函数遍历并修改同一节点数组，可能遗留旧节点；两个作者脚本改为先取得节点列表快照，再逐个删除。重建后每个图均为6个节点、1个Custom、2个正确连接的Mask。
- 修复在D3D12/SM6后台commandlet中编译；使用引擎`MaterialEditingLibrary.get_statistics`完成目标材质的着色器编译任务，再保存目标包。
- 仅处理`MountainEchoAlpineV23/M_MountainEcho_AlpineHUD`和`CadenceV1/M_Cadence_HUD`，保留其他任务和已有编辑器现场。

## 状态及边界

2026-10-28 12:24（本地时间）后台修复完成，commandlet退出码0。两个材质均已完成着色器任务、编译错误列表为空，具有1次像素纹理采样，并保存到各自原始资产路径。日志中旧材质加载时的断线错误发生在修复标记之前；修复后编译与保存阶段没有这两个材质的新编译错误。本次无需重新构建C++。

实际结果见`SourceAssets/WoodSteelLongbow20261026/ResonanceHUDRepair20261028/repair-receipt.json`及`repair-commandlet.json`；修复前两个资产保留在同目录`original/`，原始错误与首次停止保存的记录也保留。

只读运行态采样在共享接入窗口等待期间遇到编辑器关闭，未获得本次试玩的弦鸣层数。因此，本轮可以确认并修复HUD材质故障，不能声称已重现怪物/靶子的完整命中叠层链路。未主动启动游戏或PIE；用户实机复测为后续验收。
