# 201 SurfaceReform42

针对用户本轮指出的脚架衔接、机匣两侧毛躁和扳机轮廓制作。制作源及四个现用资产均已于 2026-09-29 后台保存，`delivery.json` 状态为 `current_s42_saved`；后台进程正常退出，未启动 GUI 或游戏。

- 编辑源：`LMG201_SurfaceReform42.blend`；生成入口：`model.py`。
- 枪身输入：`SightFinish41/LMG201_SightFinish41.blend`。脚架输入为本轮从当前 UE 资产导出的 `Exports/Before_Bipod*.fbx`。
- 参考：`Surface32/References/User_Left.png` 与 `User_Right.png`，以及用户本轮三张局部截图。参考图用于可见外形，不推断隐藏机构。
- 枪体新增两侧硬表面，分别制作折线凹槽和横向加强筋；替换粗糙外皮，保留原中心主体与活动盖归属。槽口采用有底凹槽、有限倒角及独立 UV。
- 前肩连接面、螺钉、槽口边缘重做。护圈改为倾斜前缘和弧形底部，连接座伸入枪体；活动扳机采用连续曲线，保留原生骨骼与 idle 逆变换。
- 脚架底座改为圆角鞍座和连续轴部外形；两根腿只重做粗糙上端与过渡套，保留转轴、下段和脚掌。
- 新表面使用当前 S41 的 191 参考金属涂层，不继承旧机匣图集法线。旧脚架下段仍保留自身 UV/材质。未修改共享材质、瞄具、动作或 C++。

后台保存入口：`run_background.ps1 -taskScript install.py -taskLog install`。它使用既有桥互斥，并在 UE 进程存在时保留现场。安装器只替换 Body / BipodBase / BipodLegA / BipodLegB，保存各目标的原文件备份；重跑依照来源及目标散列继续，遇到目标被其他工作修改则停止。

实际保存后完整导出为 `Exports/After_Body.fbx`、`After_BipodBase.fbx`、`After_BipodLegA.fbx`、`After_BipodLegB.fbx`。仅有 Parts FBX 不表示正式资产已保存。

本轮不启动编辑器或游戏，不追加渲染、自测或验收。尚无用户视觉认可，不能称为 1:1 完成。
