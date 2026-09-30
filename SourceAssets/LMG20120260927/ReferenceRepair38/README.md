# 201 ReferenceRepair38

按用户对 FitFinish37 的实机反馈返修机匣、盖壳、可见内侧和开盖露空。当前源：`LMG201_ReferenceRepair38.blend`；局部导出：`Exports/SK_LMG201_R38_ReceiverCover.fbx`。制作记录见 `../../../Docs/Weapons/lmg201-reference-repair-20260929.md`。

## 作者与接入

1. `model.py`：Blender 后台制作，读取原 Surface32/D35 机匣和 F37 未修改部件；替换失败盖体；输出专用盖体 UV、法线/AO、局部 FBX 和诊断记录。
2. `materials.py`：创建新盖体私有贴图和三个材质，沿用现有 F37 涂层及湿润参数。
3. `install.py`：备份当前运行枪体；按槽名和骨骼局部纵向归属替换机匣、盖体；保存当前加载路径与完整候选，合并天气表，输出完整装配 FBX。
4. `run_background.ps1 -taskScript integrate.py`：使用现有 UE 批次互斥；发现任何已运行 UE 进程则保留现场。不要同时启动 GUI 与 commandlet 写同一资产。

`delivery.json` 为实际保存回执，不能以脚本存在代替导入完成。`Before/` 和 `/Game/Weapons/LMG201/ReferenceRepair38/Previous` 保存修改前资产；旧 F37 几何已被用户否决，仅用于追溯。

## 定向排查

用户本轮明确要求修正尖刺、按参考图还原和镂空；`diagnose.py`、`inspect_shapes.py` 是这次排查的工具。后续不默认运行游戏或验收渲染。`closed_shape.png`、`open_shape.png`、`inside_shape.png` 是局部灰模对照，未包含完整运行组件，不能代替用户实机判断。

保留所有原骨骼、动画、布料弹箱、供弹分区、机瞄活动头部和运行挂点。未修改 C++，无需原生编译。
