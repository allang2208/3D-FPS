# SVCH 快速近战 R4 — 2026-10-20

正式保存范围是五套 SVCH GripProfile 的 `quick_melee` 条目。以 `install_receipt.json` 和 `SavedReadback/` 为准；V9 网格、权重、绑定、共享 SVD 动画以及其他动作没有写入。

最终制作链必须依次执行：

1. Python 3.11 执行 `author.py`：读取 R2 已保存姿态和 R3 已保存的既定握持手形，恢复原生骨段轴向与辅助骨站位；调用 `bend_plane.py`，按现有 ASH-12 两骨圆方法微调 20° 肘弯平面。保存后超宽投影发现收势段臂根最多越过下边界约 1.5 毫米，因此仅在该窗口加 6 毫米臂根避让，并用既有两骨 IK 保持原骨长。枪体、手掌轨迹、骨长与时序保持。
2. Blender 后台执行 `apply_existing_elbow_support.py`：直接调用工程现有 `SourceAssets/ThrustElbowRepair20260923/elbow_support.py`。按 SVD 的真实辅助骨站位校准腕侧锁定位置，保留各关节位置、腕侧辅助骨、手和手指；仅分配肘侧旋转。
3. Python 3.11 执行 `encode_profiles.py`：将第二步结果编码到五套 Profiles。
4. Blender 后台执行 `export_editable.py`：生成原生 V9 与枪体的可编辑近战动作。
5. 通过现有 UE 批次互斥运行 `install_profiles.py`；有编辑器时使用现有桥，保护 PIE 和未保存资产。脚本校对输入散列、备份旧包，只替换 quick_melee，并确认其他动作逐项不变。

不要单独重跑第二步或只运行第一步就导入。`*-not-installed.py.txt`、`native_axes*.npz`、`plane20.npz` 是未发布的制作对照；它们不是正式发布入口。R3 的 `SavedReadback/` 和安装回执仍是 R3 已保存状态的依据，R3 的作者草稿不是最终结果。

## 复核边界

`Review/` 是离线蒙皮近景。`run_native.ps1 -Modes saved-glove` 读取保存后的五套姿态，通过现有实际 Gunplay 动画图采样，`review_native.py saved-glove` 复读骨段偏移和实时 V9 修形权重。画面锚点按已有 UpdateViewmodel 的静止动作分支重建，并非游戏录像。

面法线相对邻面的反向计数会包括 V9 肘褶和指节的高曲率区域；完整保留这些数值，不把它当作严格的穿模测试，也不以后台回执宣称实机视觉验收。未启动交互游戏，未做本轮联机或第三人称验收。

## 参考流程

- `ue5-fps-arms-animation/references/grip-arm-refinement.md`：原生轴向、完整骨链与按最小幅度转动弯曲平面。
- `ue5-fps-arms-animation/references/thrust-elbow-clearance.md`：锁住肩侧与腕侧支撑，仅修正肘侧轴向旋转。
- `SourceAssets/ASH12Fix20260925/ash12_melee_fix.py::solve_side`：固定肩、手和骨长的两骨圆方法。
- `SourceAssets/ThrustElbowRepair20260923/elbow_support.py`：本次直接调用的现有肘部脚本。
