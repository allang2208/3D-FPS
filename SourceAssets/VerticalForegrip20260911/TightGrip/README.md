# 垂直握把紧握修订

本目录承接 Integration 的模型、M4 材质与运行时配件接入，修正用户指出的手掌悬空、四指未握紧问题。模型尺寸、安装点、原手臂蒙皮与右手/枪械动作不变。

## 制作方法

先查看原握姿，按握拳包握重新分配掌位、MCP/PIP/DIP 弯曲、掌骨小幅收拢及拇指对握。export_lbs.py 从原 Blender 网格导出归一化蒙皮权重，NumPy 与 Blender 实际变形顶点最大差约 2.66e-7。solve_fist.py / polish_solver.py 同时约束各指节与掌面接触，避免只追求指尖距离导致其余关节张开。apply_fist.py 保存拟合，build_animation.py 重新求解肩、肘、腕与前臂扭转链，保留骨长、缩放和手指局部平移。

松手轨迹另行处理拇指外展，完成后重新烘焙九种动作并检查原换弹接触区间。最终验收数值见 acceptance.json；生成该文件前本目录属于在验修订。

旧的 fit_tight.py、refine_tight.py、align_knuckles.py 是未采用试验，不是最终流程。最终握姿以 fist_solution.json、fit_final.json 与 M4_Vertical_Fitted.blend 为准；旧 contact_final.json 不作为验收依据。

## 本轮完成结果

- 已替换 `/Game/Weapons/M4VerticalGrip/A_M4_Vertical_*` 九条动画。掌面内收，四指各节包握，拇指形成上侧对握；配件、材质、骨长和蒙皮未改。
- `smooth_thumb_release.py` 用连续样条外展拇指，替代逐采样独立旋转。37 点轨迹相邻欧拉向量增量最大约 4.08 度；最终以真实三角面检查为准。
- `vertical-tight-v1` 新游戏进程：340 项通过，0 项失败。九条源动画结构/接触合同通过；446 个静态和过渡姿态手套/握把采样相交数为 0。静态实际变形顶点检查六组均无内部顶点。
- UE 九条动画导入及 RAW/COMPRESSED 读回通过。导入进程返回 1，原因仍为工程既有 GameFeatureData 配置及 8000 端口占用；不是无错误命令行验收。新的游戏进程独立通过。本轮未改 C++、未重新构建原生模块，也未做打包验收。
- `M4_VerticalForegrip_Integrated_Editable.blend` 包含九个动作；各动作 FBX 与 Blend、最终参数、脚本和验收记录保留。`M4_VerticalForegrip_Gameplay.mp4` 为真实游戏截帧组成的静音预览，共 159 个输入画面。
- 已查看实机第一人称、掌侧、正面、腕背和换弹回握截图。上一版 Integration 的功能与材质证据保留，但其抓握视觉已由本版替代。
- 当前打开的编辑器可能缓存旧动画；新游戏进程已读取新版。尝试连接现有编辑器的本地 MCP 初始化超时，未强制关闭用户编辑器。

当前版本：用户后续要求缩小 25% 并贴合下导轨，已由 `../Compact75/README.md` 接续。当前资源为 `/Game/Weapons/M4VerticalGripCompact75`；本目录为缩放前的紧握历史版。
