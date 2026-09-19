# 左斜握把紧握修正（2026-09-11）

本次针对握姿松散的问题：参考共振三角握把的掌面包覆和拇指对握，保持已确认的左下 45 度安装方向，以原 M4 手臂骨架与手套修正掌面位置、拇指指腹以及四指的中节和末节卷曲。未改变握把模型尺寸、导轨安装或 M4 材质。

## 源与复现

- `fit_baseline.json`：修正前参数。
- `solve_closed_fist.py` / `fist_solution.json`：受限求解与最终解。使用真实权重 LBS、指节角度限制和表面采样约束；径向距离只是拟合近似，不能代替真实模型检查。
- `apply_firm.py`：保持骨架 rest、骨长、缩放和手指局部平移，输出 `fit_final.json` 与松指曲线。
- `solve_release.py` / `release_search.json`：真实网格搜索小拇指展开速度与撤手时机；最终展开速度 1.4、撤手起点 u=0.08。
- `build_animation.py`：生成九组动作；先松指再撤手，回握逆序。原换弹取弹、插入及拍栓接触段保留。
- `M4_CantedForegrip_Integrated_Editable.blend`：汇总可编辑源；九组独立 Blender/FBX 同目录。
- `grasp_before.png` / `grasp_after.png`：相同相机的模型握姿对比。

## 游戏映射与验收

动画使用 `/Game/Weapons/M4CantedFirmGrip`；静态模型继续使用 `/Game/Weapons/M4CantedForegrip/SM_CantedForegrip`。实际检查结果见 `acceptance.json`，运行日志、导入读回与源骨架检查均保留。`M4_CantedForegrip_Gameplay.mp4` 为独立游戏进程截图按顺序制作的无声预览，不代表音频或打包构建验证。

遵循 attachment-standard、pose-contact 与 grip-arm-refinement：视觉上检查掌面与拇指对握、指节弯曲及腕臂衔接；真实变形网格 BVH 检查负责排除穿模，不把零穿模当作握紧的充分证据。
